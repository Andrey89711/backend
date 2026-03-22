from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from notifications.models import Notification
from .serializers import NotificationSerializer
from contracts.models import Concluded


def _check_payment_notifications(user):
    """Создаёт уведомления о приближающихся и просроченных платежах."""
    from notifications.utils import create_notification
    today = timezone.now().date()
    from datetime import timedelta
    three_days_later = today + timedelta(days=3)

    # Просроченные неоплаченные
    overdue = Concluded.objects.filter(is_paid=False, payment_date__lt=today)
    for c in overdue:
        if not Notification.objects.filter(
            user=user,
            message__contains=f"#{c.id_contract_id}",
            type='danger',
            created_at__date=today
        ).exists():
            create_notification(
                user,
                f"Просрочен платёж по договору #{c.id_contract_id} (был {c.payment_date})",
                'danger',
                '/agreement?tab=statuses'
            )

    # Скоро истекают (≤3 дней)
    upcoming = Concluded.objects.filter(is_paid=False, payment_date__range=[today, three_days_later])
    for c in upcoming:
        if not Notification.objects.filter(
            user=user,
            message__contains=f"#{c.id_contract_id}",
            type='warning',
            created_at__date=today
        ).exists():
            create_notification(
                user,
                f"Срок оплаты договора #{c.id_contract_id} истекает {c.payment_date}",
                'warning',
                '/agreement?tab=statuses'
            )


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        _check_payment_notifications(self.request.user)
        return Notification.objects.filter(user=self.request.user).order_by('is_read', '-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.save()
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'count': count})
