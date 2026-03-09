"""User app models are split into domain apps."""
import uuid
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin',       'Администратор'),
        ('manager',     'Менеджер'),
        ('accountant',  'Бухгалтер'),
        ('storekeeper', 'Кладовщик'),
        ('director',    'Директор'),
        ('viewer',      'Просмотр'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer', verbose_name='Роль')

    class Meta:
        db_table = 'user_profile'
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


class EmailVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_token')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_verification_token'
        verbose_name = 'Токен подтверждения email'

    def __str__(self):
        return f'Token for {self.user.username}'
