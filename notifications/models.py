from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Notification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Информация'),
        ('warning', 'Предупреждение'),
        ('danger', 'Опасность'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='Пользователь')
    message = models.TextField(verbose_name='Сообщение')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info', verbose_name='Тип')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    related_url = models.CharField(max_length=500, null=True, blank=True, verbose_name='Ссылка')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        db_table = 'notification'
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.type}] {self.message[:50]}"
