"""
Настройки для тестов. SQLite in-memory + syncdb (без запуска миграций).
Запуск: python manage.py test --settings=config.test_settings users partners contracts
"""
from .settings import *  # noqa: F401, F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Обходим запутанную историю миграций — создаём таблицы прямо из моделей
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Отключить медленный хэш паролей в тестах
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Email в памяти для проверки отправки
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
