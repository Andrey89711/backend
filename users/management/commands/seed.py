"""
Команда загрузки тестовых данных.
Запуск: python manage.py seed
Повторный запуск безопасен — все операции идемпотентны (get_or_create).
"""
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from users.models import UserProfile
from personnel.models import Director, Accountant, Manager, Storekeeper
from partners.models import Supplier
from catalog.models import Materials, Prices
from warehousing.models import Warehouse, Works, Inventory
from contracts.models import Contract, Concluded, MaterialsInContract
from deliveries.models import Delivery, ActOfArrival, AcceptanceOfDelivery
from deliveries.choices import DeliveryStatus


class Command(BaseCommand):
    help = 'Загружает тестовые данные во все таблицы'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Загрузка тестовых данных ==='))
        today = timezone.now().date()

        # ── 1. Пользователи ─────────────────────────────────────────────
        self.stdout.write('Пользователи...')
        users_data = [
            ('admin',        'admin@warehouse.ru',       True,  'admin'),
            ('manager1',     'manager1@warehouse.ru',    False, 'manager'),
            ('manager2',     'manager2@warehouse.ru',    False, 'manager'),
            ('accountant1',  'accountant1@warehouse.ru', False, 'accountant'),
            ('accountant2',  'accountant2@warehouse.ru', False, 'accountant'),
            ('storekeeper1', 'store1@warehouse.ru',      False, 'storekeeper'),
            ('storekeeper2', 'store2@warehouse.ru',      False, 'storekeeper'),
            ('storekeeper3', 'store3@warehouse.ru',      False, 'storekeeper'),
            ('director1',    'director@warehouse.ru',    False, 'director'),
            ('viewer1',      'viewer@warehouse.ru',      False, 'viewer'),
        ]
        created_users = {}
        for username, email, is_super, role in users_data:
            user, created = User.objects.get_or_create(
                username=username, defaults={'email': email, 'is_active': True}
            )
            if created:
                user.set_password('TestPass123!')
                if is_super:
                    user.is_staff = True
                    user.is_superuser = True
                user.save()
            UserProfile.objects.get_or_create(user=user, defaults={'role': role})
            created_users[username] = user
        self.stdout.write(self.style.SUCCESS(f'  OK — {len(users_data)} пользователей'))

        # ── 2. Персонал ──────────────────────────────────────────────────
        self.stdout.write('Персонал...')
        directors = []
        for name, contact in [
            ('Иванов Иван Иванович',     '+7-916-100-0001'),
            ('Петров Пётр Петрович',     '+7-916-100-0002'),
            ('Смирнов Василий Юрьевич',  '+7-916-100-0003'),
        ]:
            d, _ = Director.objects.get_or_create(
                full_name=name, defaults={'contact_information': contact}
            )
            directors.append(d)

        accountants = []
        for name, contact in [
            ('Сидорова Анна Петровна',   '+7-916-200-0001'),
            ('Козлова Мария Ивановна',   '+7-916-200-0002'),
            ('Орлова Наталья Игоревна',  '+7-916-200-0003'),
        ]:
            a, _ = Accountant.objects.get_or_create(
                full_name=name, defaults={'contact_information': contact}
            )
            accountants.append(a)

        managers = []
        for name, contact in [
            ('Новиков Алексей Сергеевич', '+7-916-300-0001'),
            ('Морозова Елена Викторовна', '+7-916-300-0002'),
            ('Белов Кирилл Андреевич',   '+7-916-300-0003'),
            ('Зайцева Оксана Романовна', '+7-916-300-0004'),
        ]:
            m, _ = Manager.objects.get_or_create(
                full_name=name, defaults={'contact_information': contact}
            )
            managers.append(m)

        storekeepers = []
        for name, contact in [
            ('Кузнецов Дмитрий Олегович', '+7-916-400-0001'),
            ('Волков Андрей Николаевич',  '+7-916-400-0002'),
            ('Тихонов Евгений Михайлович','+7-916-400-0003'),
        ]:
            s, _ = Storekeeper.objects.get_or_create(
                full_name=name, defaults={'contact_information': contact}
            )
            storekeepers.append(s)
        self.stdout.write(self.style.SUCCESS(
            f'  OK — {len(directors)} директора, {len(accountants)} бухгалтера, '
            f'{len(managers)} менеджера, {len(storekeepers)} кладовщика'
        ))

        # ── 3. Поставщики ────────────────────────────────────────────────
        self.stdout.write('Поставщики...')
        suppliers_raw = [
            ('ООО СтройМатериал',      '7701234567', 'Зайцев К.В.',    'Романов А.Д.',   'р/с 40702810100000000001, БИК 044525001', 'active'),
            ('ЗАО МеталлТорг',         '7709876543', 'Лебедев О.П.',   'Семёнов Г.В.',   'р/с 40702810100000000002, БИК 044525002', 'active'),
            ('ООО ЛесопромСервис',     '7723456789', 'Попова Е.В.',    'Григорьев Д.С.', 'р/с 40702810100000000003, БИК 044525003', 'active'),
            ('ИП Воробьёв С.А.',       '771122334',  'Воробьёв С.А.',  'Воробьёв С.А.',  'р/с 40802810100000000004, БИК 044525004', 'approved'),
            ('ООО СтройИнвест Групп',  '7756789012', 'Тарасов В.Н.',   'Федоров А.П.',   'р/с 40702810100000000005, БИК 044525005', 'approved'),
            ('ЗАО КаменьСтрой',        '7734567890', 'Михайлов С.Е.',  'Ильин Р.А.',     'р/с 40702810100000000006, БИК 044525006', 'pending'),
        ]
        suppliers = []
        for name, tax_id, acc_fn, dir_fn, details, st in suppliers_raw:
            sup, _ = Supplier.objects.get_or_create(tax_id=tax_id, defaults={
                'name': name, 'accounted_full_name': acc_fn,
                'director_full_name': dir_fn, 'payment_details': details, 'status': st
            })
            suppliers.append(sup)
        self.stdout.write(self.style.SUCCESS(f'  OK — {len(suppliers)} поставщиков'))

        # ── 4. Материалы ─────────────────────────────────────────────────
        self.stdout.write('Материалы...')
        materials_raw = [
            ('Цемент М400',        'меш.',  'Портландцемент марки М400, мешки по 50 кг'),
            ('Цемент М500',        'меш.',  'Портландцемент марки М500, мешки по 50 кг'),
            ('Кирпич красный',     'шт.',   'Керамический полнотелый кирпич 250x120x65 мм'),
            ('Кирпич силикатный',  'шт.',   'Силикатный кирпич М150, 250x120x65 мм'),
            ('Арматура Ø12',       'п.м.',  'Стальная рифленая арматура диаметром 12 мм, А500С'),
            ('Арматура Ø16',       'п.м.',  'Стальная рифленая арматура диаметром 16 мм, А500С'),
            ('Доска обрезная',     'м³',    'Хвойная обрезная доска 50x150 мм, сорт 2'),
            ('Брус строительный',  'м³',    'Хвойный строительный брус 100x100 мм, сорт 1'),
            ('Песок речной',       'т',     'Строительный мытый речной песок, модуль крупности 2.0'),
            ('Щебень фракция 20',  'т',     'Гранитный щебень фракции 20-40 мм'),
            ('Пенополистирол 50',  'м²',    'Утеплитель пенополистирол ПСБ-С 50 мм, плотность 25 кг/м³'),
            ('Рубероид РКП-350',   'рул.',  'Рубероид кровельный с посыпкой, рулон 15 м²'),
        ]
        materials = []
        for name, unit, desc in materials_raw:
            mat, _ = Materials.objects.get_or_create(name=name, defaults={
                'unit_of_measurement': unit, 'description': desc
            })
            materials.append(mat)
        self.stdout.write(self.style.SUCCESS(f'  OK — {len(materials)} материалов'))

        # ── 5. Цены ──────────────────────────────────────────────────────
        self.stdout.write('Цены...')
        # Несколько исторических цен + текущая
        price_dates = [
            today - datetime.timedelta(days=90),
            today - datetime.timedelta(days=30),
            today,
        ]
        prices_raw = [
            # (материал, поставщик, [цены по датам])
            (materials[0],  suppliers[0], [420.0, 435.0, 450.0]),
            (materials[0],  suppliers[1], [460.0, 470.0, 480.0]),
            (materials[1],  suppliers[0], [490.0, 500.0, 515.0]),
            (materials[2],  suppliers[0], [17.0,  18.0,  18.5]),
            (materials[2],  suppliers[2], [16.5,  17.0,  17.8]),
            (materials[3],  suppliers[3], [12.0,  12.5,  13.0]),
            (materials[4],  suppliers[1], [88.0,  92.0,  95.0]),
            (materials[5],  suppliers[1], [110.0, 118.0, 125.0]),
            (materials[6],  suppliers[2], [11000.0, 11500.0, 12000.0]),
            (materials[7],  suppliers[2], [14000.0, 14500.0, 15000.0]),
            (materials[8],  suppliers[3], [780.0, 820.0, 850.0]),
            (materials[9],  suppliers[4], [1100.0, 1150.0, 1200.0]),
            (materials[10], suppliers[4], [95.0,  98.0,  100.0]),
            (materials[11], suppliers[5], [380.0, 390.0, 400.0]),
        ]
        price_count = 0
        for mat, sup, prices in prices_raw:
            for date, price in zip(price_dates, prices):
                Prices.objects.get_or_create(
                    id_materials=mat, id_supplier=sup, effective_dates=date,
                    defaults={'price': price}
                )
                price_count += 1
        self.stdout.write(self.style.SUCCESS(f'  OK — {price_count} записей цен'))

        # ── 6. Склады и назначения ───────────────────────────────────────
        self.stdout.write('Склады...')
        warehouses = []
        for name, address in [
            ('Склад №1 (Главный)',    'г. Москва, ул. Складская, д. 1'),
            ('Склад №2 (Материалы)',  'г. Москва, ул. Промышленная, д. 5'),
            ('Склад №3 (Резервный)',  'г. Подольск, ул. Заводская, д. 12'),
        ]:
            wh, _ = Warehouse.objects.get_or_create(
                name=name, defaults={'address': address}
            )
            warehouses.append(wh)

        # Привязка кладовщиков к складам
        for sk, wh in [
            (storekeepers[0], warehouses[0]),
            (storekeepers[1], warehouses[1]),
            (storekeepers[2], warehouses[2]),
        ]:
            Works.objects.get_or_create(id_storekeeper=sk, id_warehouse=wh)

        # Начальные остатки
        inventory_raw = [
            (materials[0],  warehouses[0], 500.0),
            (materials[1],  warehouses[0], 200.0),
            (materials[2],  warehouses[0], 10000.0),
            (materials[3],  warehouses[0], 5000.0),
            (materials[4],  warehouses[1], 800.0),
            (materials[5],  warehouses[1], 400.0),
            (materials[6],  warehouses[1], 45.0),
            (materials[7],  warehouses[1], 20.0),
            (materials[8],  warehouses[2], 150.0),
            (materials[9],  warehouses[2], 80.0),
            (materials[10], warehouses[2], 600.0),
            (materials[11], warehouses[2], 120.0),
        ]
        for mat, wh, qty in inventory_raw:
            Inventory.objects.get_or_create(
                id_warehouse=wh, id_materials=mat,
                defaults={'quantity': qty}
            )
        self.stdout.write(self.style.SUCCESS(
            f'  OK — {len(warehouses)} склада, {len(inventory_raw)} позиций остатков'
        ))

        # ── 7. Контракты и договоры ──────────────────────────────────────
        self.stdout.write('Контракты и договоры...')

        # Создаём 8 контрактов с разными статусами
        contract_statuses = ['active', 'active', 'active', 'review', 'review', 'draft', 'closed', 'closed']
        contracts = []
        for st in contract_statuses:
            c = Contract.objects.create(status=st)
            contracts.append(c)

        # Заключённые договоры для 6 из 8 контрактов
        concluded_raw = [
            # (contract, supplier, accountant, manager, director, days_ago_concluded, days_payment, cost)
            (contracts[0], suppliers[0], accountants[0], managers[0], directors[0], 60,  30,  1_250_000.00),
            (contracts[1], suppliers[1], accountants[1], managers[1], directors[1], 45,  15,    780_000.00),
            (contracts[2], suppliers[2], accountants[2], managers[2], directors[2], 30,  60,    450_000.00),
            (contracts[3], suppliers[0], accountants[0], managers[3], directors[0], 10,  45,    320_000.00),
            (contracts[6], suppliers[4], accountants[1], managers[0], directors[1], 120, -10,   960_000.00),  # просрочен
            (contracts[7], suppliers[3], accountants[2], managers[1], directors[2], 180, -30, 2_100_000.00),  # закрыт
        ]
        concluded_list = []
        for contract, sup, acc, mgr, dr, days_ago, days_pay, cost in concluded_raw:
            c_date = today - datetime.timedelta(days=days_ago)
            p_date = today + datetime.timedelta(days=days_pay)
            concluded, _ = Concluded.objects.get_or_create(id_contract=contract, defaults={
                'id_supplier': sup, 'id_accountant': acc, 'id_manager': mgr,
                'id_director': dr, 'conclusion_dates': c_date,
                'payment_date': p_date, 'cost': cost
            })
            concluded_list.append(concluded)

        # Материалы в договорах
        mic_raw = [
            (contracts[0], materials[0],  500.0, 500.0,  'Отличное'),
            (contracts[0], materials[2],  5000.0, 4800.0,'Хорошее'),
            (contracts[0], materials[4],  200.0, 200.0,  'Хорошее'),
            (contracts[1], materials[5],  100.0, 95.0,   'Хорошее'),
            (contracts[1], materials[6],  20.0,  18.0,   'Удовлетворительное'),
            (contracts[2], materials[8],  80.0,  80.0,   'Хорошее'),
            (contracts[2], materials[9],  50.0,  45.0,   'Хорошее'),
            (contracts[3], materials[1],  300.0, 0.0,    'Не принято'),
            (contracts[3], materials[3],  2000.0, 0.0,   'Не принято'),
            (contracts[6], materials[10], 1000.0, 1000.0,'Отличное'),
            (contracts[6], materials[11], 500.0, 500.0,  'Хорошее'),
            (contracts[7], materials[7],  40.0,  40.0,   'Хорошее'),
        ]
        for contract, mat, qty_plan, qty_actual, cond in mic_raw:
            MaterialsInContract.objects.get_or_create(
                id_contract=contract, id_materials=mat,
                defaults={'materials_quality_in_contract': qty_plan,
                          'actual_quantity': qty_actual, 'condition': cond}
            )
        self.stdout.write(self.style.SUCCESS(
            f'  OK — {len(contracts)} контрактов, {len(concluded_list)} заключённых, '
            f'{len(mic_raw)} позиций материалов'
        ))

        # ── 8. Акты прибытия ─────────────────────────────────────────────
        self.stdout.write('Поставки и акты прибытия...')

        acts_data = [
            DeliveryStatus.RECEIVED,   # act 1 — принято
            DeliveryStatus.DELIVERED,  # act 2 — доставлено, ожидает приёмки
            DeliveryStatus.DELIVERED,  # act 3
            DeliveryStatus.PENDING,    # act 4 — ещё едет
            DeliveryStatus.PENDING,    # act 5
            DeliveryStatus.PENDING,    # act 6 — задержка
        ]
        acts = []
        for st in acts_data:
            act = ActOfArrival.objects.create(status=st)
            acts.append(act)

        # Поставки
        deliveries_raw = [
            # (contract, status, days_delta, act)
            (contracts[0], DeliveryStatus.RECEIVED,     -55, acts[0]),
            (contracts[1], DeliveryStatus.DELIVERED,    -3,  acts[1]),
            (contracts[2], DeliveryStatus.IN_TRANSIT,   +2,  acts[2]),
            (contracts[3], DeliveryStatus.PENDING,      +5,  acts[3]),
            (contracts[6], DeliveryStatus.DELIVERED,    -115,acts[4]),
            (contracts[7], DeliveryStatus.DELAYED,      -10, acts[5]),  # задержана
        ]
        deliveries = []
        for contract, st, delta, act in deliveries_raw:
            d, _ = Delivery.objects.get_or_create(
                id_contract=contract,
                defaults={
                    'status': st,
                    'delivery_date': today + datetime.timedelta(days=delta),
                    'id_act_of_arrival': act
                }
            )
            deliveries.append(d)

        # Приёмка для первой поставки (с auto-обновлением склада)
        AcceptanceOfDelivery.objects.get_or_create(
            id_storekeeper=storekeepers[0],
            id_act_of_arrival=acts[0],
        )
        self.stdout.write(self.style.SUCCESS(
            f'  OK — {len(acts)} актов прибытия, {len(deliveries)} поставок, 1 приёмка'
        ))

        # ── Итог ─────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('OK! Тестовые данные успешно загружены!'))
        self.stdout.write('')
        self.stdout.write('Учётные записи (пароль у всех: TestPass123!):')
        self.stdout.write('  admin        — суперпользователь (Django admin)')
        self.stdout.write('  manager1/2   — менеджер')
        self.stdout.write('  accountant1/2— бухгалтер')
        self.stdout.write('  storekeeper1/2/3 — кладовщик')
        self.stdout.write('  director1    — директор')
        self.stdout.write('  viewer1      — просмотр (только чтение)')
        self.stdout.write('')
        self.stdout.write('Swagger: http://localhost:8000/api/docs/')
