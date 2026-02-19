# Backend - система управления складом

Backend-часть проекта на Django/DRF с JWT-аутентификацией и MySQL.

## Стек

- Python 3.10+
- Django 6
- Django REST Framework
- Simple JWT
- MySQL
- drf-spectacular (Swagger/OpenAPI)
- django-cors-headers

## Архитектура приложений

Проект разделен по бизнес-доменам:

- `users` - auth (регистрация, логин, refresh, logout, профиль)
- `personnel` - сотрудники (бухгалтер, директор, менеджер, кладовщик)
- `partners` - поставщики
- `catalog` - материалы и цены
- `warehousing` - склады, остатки, привязка кладовщиков к складам
- `contracts` - договоры и состав материалов в договорах
- `deliveries` - поставки, акты прибытия, приемка поставки

## Быстрый старт

1. Перейти в корень проекта:

```bash
cd backend
```

2. Создать и активировать виртуальное окружение:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Установить зависимости:

```bash
pip install -r requirements.txt
```

4. Создать файл `backend/.env`:

```env
SECRET_KEY=django-insecure-change-me
DEBUG=True

DB_ENGINE=django.db.backends.mysql
DB_NAME=core
DB_USER=root
DB_PASSWORD=root
DB_HOST=localhost
DB_PORT=3306
```

5. Создать БД в MySQL (если еще не создана):

```sql
CREATE DATABASE core CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

6. Выполнить миграции:

```bash
python manage.py makemigrations
python manage.py migrate
```

7. (Опционально) создать суперпользователя:

```bash
python manage.py createsuperuser
```

8. Запустить сервер:

```bash
python manage.py runserver
```

## Сидирование тестовых данных

Из корня `backend`:

```bash
python data_set.py
```

## API

- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`

Основные префиксы:

- `api/auth/`
- `api/personnel/`
- `api/partners/`
- `api/catalog/`
- `api/warehousing/`
- `api/contracts/`
- `api/deliveries/`

## Важно по миграциям

Если используется старая база, где уже есть таблицы доменных моделей из прежнего `users`, возможны конфликты вида `Table ... already exists`.  
В таком случае применяйте старые миграции `users` как `fake`:

```bash
python manage.py migrate users 0001 --fake
python manage.py migrate users 0002 --fake
python manage.py migrate
```

## Актуальная структура (сокращенно)

```text
backend/
  config/
  users/
  personnel/
  partners/
  catalog/
  warehousing/
  contracts/
  deliveries/
  manage.py
  data_set.py
  requirements.txt
  README.md
```
