"""Утилита для создания уведомлений из любого места приложения."""
import logging
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


def create_notification(user, message, notif_type='info', url=None):
    """Создаёт уведомление для конкретного пользователя."""
    try:
        from notifications.models import Notification
        Notification.objects.create(
            user=user,
            message=message,
            type=notif_type,
            related_url=url,
        )
    except Exception as e:
        logger.error(f"Ошибка создания уведомления для {user}: {e}")


def create_notification_for_role(role, message, notif_type='info', url=None):
    """Создаёт уведомление для всех пользователей с указанной ролью."""
    try:
        from users.models import UserProfile
        profiles = UserProfile.objects.filter(role=role).select_related('user')
        for profile in profiles:
            create_notification(profile.user, message, notif_type, url)
    except Exception as e:
        logger.error(f"Ошибка создания уведомлений для роли {role}: {e}")
