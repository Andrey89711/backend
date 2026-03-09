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

## Тестовые данные

Загрузить полный набор тестовых данных:

```bash
python manage.py seed
```

Команда идемпотентна — повторный запуск безопасен. Создаёт:
- 10 пользователей (все роли)
- 3 директора, 3 бухгалтера, 4 менеджера, 3 кладовщика
- 6 поставщиков (active / approved / pending)
- 12 материалов с историей цен от 3 поставщиков
- 3 склада, 12 позиций инвентаря
- 8 контрактов (active / review / draft / closed) + 6 заключённых договоров
- 6 поставок с разными статусами (включая просроченные и задержанные)

**Учётные записи** (пароль у всех: `TestPass123!`):

| Логин | Роль | Доступ |
|---|---|---|
| `admin` | Администратор | Всё + Django Admin |
| `manager1`, `manager2` | Менеджер | Контракты, Статистика |
| `accountant1`, `accountant2` | Бухгалтер | Контракты |
| `storekeeper1/2/3` | Кладовщик | Склады, Поставки |
| `director1` | Директор | Контракты, Статистика |
| `viewer1` | Просмотр | Только чтение |

## Тестирование

```bash
# Запуск всех тестов (SQLite in-memory, без миграций)
python manage.py test users partners contracts --settings=config.test_settings

# С подробным выводом
python manage.py test users partners contracts --settings=config.test_settings -v 2
```

## API

- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`

Все эндпоинты требуют JWT-токен в заголовке, кроме `register`, `login`, `token/refresh`, `verify-email`.

### Аутентификация (`api/auth/`)

| Метод | URL | Описание |
|---|---|---|
| POST | `register/` | Регистрация (создаёт неактивного пользователя, отправляет письмо) |
| POST | `login/` | Вход → `{ access, refresh, user }` |
| POST | `token/refresh/` | Обновление access-токена |
| POST | `logout/` | Инвалидация refresh-токена |
| GET  | `me/` | Профиль текущего пользователя (включает `role`) |
| GET  | `verify-email/?token=...` | Подтверждение email |

### Основные ресурсы

| Префикс | Ресурс | Дополнительные action |
|---|---|---|
| `api/personnel/` | directors, accountants, managers, storekeepers | — |
| `api/partners/` | suppliers | `{id}/set-status/`, `{id}/today-prices/`, `{id}/price-trend/` |
| `api/catalog/` | materials, prices | — |
| `api/warehousing/` | warehouses, works, inventory | — |
| `api/contracts/` | contracts, concluded, materials | `{id}/set-status/`, `{id}/file/download/`, `concluded/statistics/`, `concluded/by_manager/` |
| `api/deliveries/` | deliveries, acts-of-arrival, acceptances | `deliveries/alerts/`, `deliveries/pending_today/`, `{id}/set_arrived/` |
| `api/contracts/documents/` | — | `upload_docx/`, `list_files/`, `download/` |

### Статусы

**Поставщик:** `pending` → `approved` → `active`

**Договор:** `draft` → `review` → `active` → `closed`

**Поставка:** `Pending` → `In Transit` → `Delivered` → `Received` | `Not Delivered` | `Delayed` | `Cancel`

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

## DOCX to PDF converter

From `backend` directory:

```bash
$env:Path += ";C:\Program Files\LibreOffice\program"
```

```bash
pip install -r requirements.txt
python docx_to_pdf.py input.docx
python docx_to_pdf.py input.docx -o output.pdf
```

Notes:

- Primary method: `docx2pdf` (requires Microsoft Word on Windows).
- Fallback method: LibreOffice (`soffice` in PATH).
