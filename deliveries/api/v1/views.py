import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from deliveries.models import AcceptanceOfDelivery, ActOfArrival, Delivery
from .serializers import DeliverySerializer, ActOfArrivalSerializer, AcceptanceOfDeliverySerializer
from ...choices import DeliveryStatus
from contracts.models import MaterialsInContract
from warehousing.models import Inventory, Works

logger = logging.getLogger(__name__)
class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all().select_related('id_contract', 'id_act_of_arrival')
    serializer_class = DeliverySerializer

    @action(detail=False, methods=['get'])
    def  alerts(self, request):
        """
        Сводка проблемных зон: задержки и непринятые акты.
        URL: /api/catalog/deliveries/alerts/
        """
        today = timezone.now().date()
        
        
        three_days_ago = today - timedelta(days=3)
        overdue = Delivery.objects.filter(
            status__in=[
                DeliveryStatus.IN_TRANSIT, 
                DeliveryStatus.PENDING, 
                DeliveryStatus.DELAYED], 
            delivery_date__lt=three_days_ago
        )
        
        # 2. Акты прибытия, которые еще не прошли приемку кладовщиком
        # Фильтруем через обратную связь (related_name или имя модели в нижнем регистре)
        unaccepted = ActOfArrival.objects.filter(acceptanceofdelivery__isnull=True)
        
        return Response({
            "overdue_count": overdue.count(),
            "unaccepted_acts_count": unaccepted.count(),
            "status_summary": {
                "in_transit": DeliveryStatus.IN_TRANSIT.label,
                "pending": DeliveryStatus.PENDING.label
            }
        })

    @action(detail=False, methods=['get'])
    def pending_today(self, request):
        """Поставки, ожидаемые сегодня со статусом 'Не доставлено'"""
        today = timezone.now().date()
        qs = self.queryset.filter(
            delivery_date=today, 
            status__in=[DeliveryStatus.PENDING, DeliveryStatus.IN_TRANSIT, DeliveryStatus.NOT_DELIVERED]
            ) # Добавить и поменять статус на ожидаеться 
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def set_arrived(self, request, pk=None):
        """Быстрый перевод конкретной поставки в статус 'Доставлено'"""
        delivery = self.get_object()
        delivery.status = DeliveryStatus.DELIVERED
        delivery.save()
        return Response({'status': f'Поставка #{pk} отмечена как доставленная'})

class ActOfArrivalViewSet(viewsets.ModelViewSet):
    queryset = ActOfArrival.objects.all()
    serializer_class = ActOfArrivalSerializer

    @action(detail=False, methods=['get'])
    def without_acceptance(self, request):
        """Акты, которые еще не прошли процедуру приемки кладовщиком"""
        # Ищем акты, для которых нет записи в AcceptanceOfDelivery
        qs = self.queryset.filter(acceptanceofdelivery__isnull=True)
        return Response(self.get_serializer(qs, many=True).data)

class AcceptanceOfDeliveryViewSet(viewsets.ModelViewSet):
    queryset = AcceptanceOfDelivery.objects.all().select_related('id_storekeeper', 'id_act_of_arrival')
    serializer_class = AcceptanceOfDeliverySerializer

    def create(self, request, *args, **kwargs):
        """Создаём приемку, обновляем статус акта и остатки склада."""
        response = super().create(request, *args, **kwargs)

        act_id = request.data.get('id_act_of_arrival')
        storekeeper_id = request.data.get('id_storekeeper')

        if act_id:
            try:
                act = ActOfArrival.objects.get(pk=act_id)
                act.status = 'RECEIVED'
                act.save()
            except ActOfArrival.DoesNotExist:
                logger.warning(f"ActOfArrival pk={act_id} не найден при создании приемки")

        # Автообновление складских остатков
        if act_id and storekeeper_id:
            try:
                # Находим склад кладовщика
                works_qs = Works.objects.filter(id_storekeeper_id=storekeeper_id)
                if not works_qs.exists():
                    logger.warning(f"Кладовщик id={storekeeper_id} не привязан ни к одному складу")
                else:
                    warehouse = works_qs.first().id_warehouse

                    # Находим контракт через поставку
                    delivery = Delivery.objects.filter(id_act_of_arrival_id=act_id).first()
                    if delivery and delivery.id_contract_id:
                        materials_qs = MaterialsInContract.objects.filter(
                            id_contract_id=delivery.id_contract_id
                        ).select_related('id_materials')

                        for mic in materials_qs:
                            qty = mic.actual_quantity or 0
                            if qty <= 0:
                                continue
                            inv, created = Inventory.objects.get_or_create(
                                id_warehouse=warehouse,
                                id_materials=mic.id_materials,
                                defaults={'quantity': 0}
                            )
                            inv.quantity += qty
                            inv.save()
                            logger.info(
                                f"Склад {warehouse.id_warehouse}: материал "
                                f"{mic.id_materials_id} +{qty} (итого {inv.quantity})"
                            )
                    else:
                        logger.warning(f"Поставка для акта id={act_id} не найдена или без контракта")
            except Exception as e:
                logger.error(f"Ошибка обновления остатков при приемке: {e}", exc_info=True)

        return response
