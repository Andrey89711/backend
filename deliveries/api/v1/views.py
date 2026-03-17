import logging
from django.db.models import Sum
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


def _auto_delay(qs):
    """Помечает просроченные доставки как DELAYED."""
    today = timezone.now().date()
    not_terminal = [DeliveryStatus.IN_TRANSIT, DeliveryStatus.PENDING, DeliveryStatus.NOT_DELIVERED]
    qs.filter(delivery_date__lt=today, status__in=not_terminal).update(status=DeliveryStatus.DELAYED)


class DeliveryViewSet(viewsets.ModelViewSet):
    serializer_class = DeliverySerializer

    def get_queryset(self):
        qs = Delivery.objects.all().select_related('id_contract', 'id_act_of_arrival')
        _auto_delay(qs)
        return qs

    @action(detail=False, methods=['get'])
    def alerts(self, request):
        today = timezone.now().date()
        three_days_ago = today - timedelta(days=3)
        qs = self.get_queryset()
        overdue = qs.filter(
            status__in=[DeliveryStatus.IN_TRANSIT, DeliveryStatus.PENDING, DeliveryStatus.DELAYED],
            delivery_date__lt=three_days_ago
        )
        unaccepted = ActOfArrival.objects.filter(acceptanceofdelivery__isnull=True)
        return Response({
            "overdue_count": overdue.count(),
            "unaccepted_acts_count": unaccepted.count(),
        })

    @action(detail=False, methods=['get'])
    def pending_today(self, request):
        today = timezone.now().date()
        qs = self.get_queryset().filter(
            delivery_date=today,
            status__in=[DeliveryStatus.PENDING, DeliveryStatus.IN_TRANSIT, DeliveryStatus.NOT_DELIVERED]
        )
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def set_arrived(self, request, pk=None):
        delivery = self.get_object()
        delivery.status = DeliveryStatus.DELIVERED
        delivery.save()
        try:
            from notifications.utils import create_notification_for_role
            create_notification_for_role(
                'storekeeper',
                f"Доставка #{delivery.pk} прибыла. Необходима приёмка.",
                'info',
                '/delivery',
            )
        except Exception as e:
            logger.warning(f"Ошибка уведомления: {e}")
        return Response({'status': f'Поставка #{pk} отмечена как доставленная'})


class ActOfArrivalViewSet(viewsets.ModelViewSet):
    queryset = ActOfArrival.objects.all()
    serializer_class = ActOfArrivalSerializer

    @action(detail=False, methods=['get'])
    def without_acceptance(self, request):
        qs = self.queryset.filter(acceptanceofdelivery__isnull=True)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def start_receiving(self, request, pk=None):
        """Начало приёмки — меняет статус акта на 'Осуществление приёма'."""
        act = self.get_object()
        act.status = DeliveryStatus.RECEIVING
        act.save()
        return Response(self.get_serializer(act).data)

    @action(detail=True, methods=['post'])
    def confirm_acceptance(self, request, pk=None):
        """
        Подтверждение приёмки.
        Body: { storekeeper_id: N, items: [{material_id, actual_quantity, condition}, ...] }
        """
        act = self.get_object()
        storekeeper_id = request.data.get('storekeeper_id')
        items = request.data.get('items', [])

        if not storekeeper_id:
            return Response({'error': 'storekeeper_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Обновляем actual_quantity и condition в MaterialsInContract
        delivery = Delivery.objects.filter(id_act_of_arrival=act).first()
        if delivery:
            for item in items:
                mat_id = item.get('material_id')
                actual_qty = item.get('actual_quantity')
                cond = item.get('condition', '')
                MaterialsInContract.objects.filter(
                    id_contract=delivery.id_contract,
                    id_materials_id=mat_id
                ).update(actual_quantity=actual_qty, condition=cond)

        # 2. Создаём AcceptanceOfDelivery
        try:
            acceptance = AcceptanceOfDelivery.objects.create(
                id_storekeeper_id=storekeeper_id,
                id_act_of_arrival=act
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Меняем статус акта
        act.status = DeliveryStatus.RECEIVED
        act.save()

        # 4. Обновляем остатки на складе
        if delivery:
            try:
                works_qs = Works.objects.filter(id_storekeeper_id=storekeeper_id)
                if works_qs.exists():
                    warehouse = works_qs.first().id_warehouse
                    materials_qs = MaterialsInContract.objects.filter(
                        id_contract=delivery.id_contract
                    ).select_related('id_materials')
                    for mic in materials_qs:
                        qty = mic.actual_quantity or 0
                        if qty <= 0:
                            continue
                        inv, _ = Inventory.objects.get_or_create(
                            id_warehouse=warehouse,
                            id_materials=mic.id_materials,
                            defaults={'quantity': 0}
                        )
                        inv.quantity += qty
                        inv.save(update_fields=['quantity'])

                    _check_min_stock_notifications(materials_qs)
            except Exception as e:
                logger.error(f"Ошибка обновления остатков: {e}", exc_info=True)

        # 5. Уведомления
        try:
            from notifications.utils import create_notification_for_role
            create_notification_for_role(
                'manager',
                f"Акт прихода #{act.pk} подтверждён. Материалы добавлены на склад.",
                'info',
                '/delivery',
            )
        except Exception as e:
            logger.warning(f"Ошибка уведомления: {e}")

        return Response({
            'status': 'accepted',
            'acceptance_id': acceptance.pk,
            'act_status': act.status,
        })


def _check_min_stock_notifications(materials_qs):
    """Создаёт уведомления если остаток упал ниже минимума."""
    try:
        from notifications.utils import create_notification_for_role
        for mic in materials_qs:
            mat = mic.id_materials
            if mat.min_quantity is None:
                continue
            total = Inventory.objects.filter(id_materials=mat).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            if total < mat.min_quantity:
                create_notification_for_role(
                    'storekeeper',
                    f"Остаток материала '{mat.name}' ({total}) ниже минимума ({mat.min_quantity})",
                    'warning',
                    '/main-actions',
                )
    except Exception as e:
        logger.error(f"Ошибка проверки min_stock: {e}")


class AcceptanceOfDeliveryViewSet(viewsets.ModelViewSet):
    queryset = AcceptanceOfDelivery.objects.all().select_related('id_storekeeper', 'id_act_of_arrival')
    serializer_class = AcceptanceOfDeliverySerializer
