# Backend - Система управления складом

**Django + DRF + JWT + MySQL** - Бэкенд часть системы управления складом (аутентификация).

---

## Содержание

- [Описание проекта](#)
- [Технологии](#)
- [Требования к системе](#)
- [Быстрый старт](#)
- [Структура проекта](#)
- [API Документация](#)
- [Развертывание](#)

---

## Описание проекта

Система управления складом с модулями:
- 📦 Управление складами и остатками
- 📝 Управление материалами и поставщиками
- 📊 Отслеживание поставок и договоров
- 👥 Управление персоналом
- 🔐 Аутентификация через JWT

---

## Технологии

| Технология | Версия | Назначение |
|------------|--------|------------|
| **Python** | 3.10+ | Язык программирования |
| **Django** | 5.0+ | Web-фреймворк |
| **Django REST Framework** | 3.14+ | API фреймворк |
| **djangorestframework-simplejwt** | 5.3+ | JWT аутентификация |
| **MySQL** | 8.0+ | База данных |
| **drf-spectacular** | 0.26+ | Авто-документация API |
| **django-cors-headers** | 4.3+ | CORS поддержка |

---

## Требования к системе

### Минимальные требования
- **ОС**: Windows 10/11, Linux, macOS
- **Python**: 3.10 или выше
- **MySQL**: 8.0 или выше
- **RAM**: 2 ГБ
- **Дисковое пространство**: 500 МБ

### Рекомендуемые требования
- **RAM**: 4 ГБ
- **Дисковое пространство**: 1 ГБ
- **MySQL**: 8.0+ с поддержкой UTF8MB4

---

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd backend
```

### 2. Создание виртуального окружения
#### Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux/Mac:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения
Создайте файл .env в корне проекта:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DB_NAME=warehouse_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
```

### 5. Создание базы данных MySQL
```bash
-- Подключение к MySQL
mysql -u root -p

-- Создание базы данных
CREATE DATABASE warehouse_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Проверка
SHOW DATABASES;
```

### 6. Применение миграций
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Создание суперпользователя
```bash
python manage.py createsuperuser
```

### 8. Запуск
```bash
python manage.py runserver
```

## Структура проекта
```bash
backend/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── users/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── .env
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

### Авто-документация
##### После запуска сервера доступна документация:
```bash
Swagger UI: http://localhost:8000/api/docs/
ReDoc: http://localhost:8000/api/schema/
```
