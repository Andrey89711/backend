from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from deliveries.models import AcceptanceOfDelivery, ActOfArrival, Delivery
from .serializers import DeliverySerializer, ActOfArrivalSerializer, AcceptanceOfDeliverySerializer

class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all().select_related('id_contract', 'id_act_of_arrival')
    serializer_class = DeliverySerializer

    @action(detail=False, methods=['get'])
    def  problem(self, request):
        """
        Сводка проблемных зон: задержки и непринятые акты.
        URL: /api/catalog/deliveries/alerts/
        """
        today = timezone.now().date()
        
        # 1. Поставки, которые задерживаются более чем на 3 дня (статус 'В пути' или 'Не доставлено')
        three_days_ago = today - timedelta(days=3)
        overdue = Delivery.objects.filter(
            status__in=['Не доставлено'], # Добавить статус задерживаеться  
            delivery_date__lt=three_days_ago
        )
        
        # 2. Акты прибытия, которые еще не прошли приемку кладовщиком
        # Фильтруем через обратную связь (related_name или имя модели в нижнем регистре)
        unaccepted = ActOfArrival.objects.filter(acceptanceofdelivery__isnull=True)
        
        return Response({
            "overdue_count": overdue.count(),
            "unaccepted_acts_count": unaccepted.count(),
            "date": today
        })

    @action(detail=False, methods=['get'])
    def pending_today(self, request):
        """Поставки, ожидаемые сегодня со статусом 'Не доставлено'"""
        today = timezone.now().date()
        qs = self.queryset.filter(delivery_date=today, status='Не доставлено') # Добавить и поменять статус на ожидаеться 
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def set_arrived(self, request, pk=None):
        """Быстрый перевод конкретной поставки в статус 'Доставлено'"""
        delivery = self.get_object()
        delivery.status = 'Доставлено'
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
        """Переопределяем создание, чтобы автоматически менять статус акта при приемке"""
        response = super().create(request, *args, **kwargs)
        # Если приемка создана, находим акт и обновляем его статус
        act_id = request.data.get('id_act_of_arrival')
        if act_id:
            act = ActOfArrival.objects.get(pk=act_id)
            act.status = 'RECEIVED' # Или ваш статус из DeliveryStatus
            act.save()
        return response
