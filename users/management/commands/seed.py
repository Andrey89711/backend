"""
РљРѕРјР°РЅРґР° Р·Р°РіСЂСѓР·РєРё С‚РµСЃС‚РѕРІС‹С… РґР°РЅРЅС‹С….
Р—Р°РїСѓСЃРє: python manage.py seed
РџРѕРІС‚РѕСЂРЅС‹Р№ Р·Р°РїСѓСЃРє Р±РµР·РѕРїР°СЃРµРЅ вЂ” РІСЃРµ РѕРїРµСЂР°С†РёРё РёРґРµРјРїРѕС‚РµРЅС‚РЅС‹ (get_or_create).
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
    help = 'Р—Р°РіСЂСѓР¶Р°РµС‚ С‚РµСЃС‚РѕРІС‹Рµ РґР°РЅРЅС‹Рµ РІРѕ РІСЃРµ С‚Р°Р±Р»РёС†С‹'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Р—Р°РіСЂСѓР·РєР° С‚РµСЃС‚РѕРІС‹С… РґР°РЅРЅС‹С… ==='))
        today = timezone.now().date()

        # в”Ђв”Ђ 1. РџРѕР»СЊР·РѕРІР°С‚РµР»Рё в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        self.stdout.write('РџРѕР»СЊР·РѕРІР°С‚РµР»Рё...')
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
        self.stdout.write(self.style.SUCCESS(f'  OK вЂ” {len(users_data)} РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№'))

        # в”Ђв”Ђ 2. РџРµСЂСЃРѕРЅР°Р» в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        self.stdout.write('РџРµСЂСЃРѕРЅР°Р»...')
        directors = []
        for name, contact in [
            ('РРІР°РЅРѕРІ РРІР°РЅ РРІР°РЅРѕРІРёС‡',     '+7-916-100-0001'),
            ('РџРµС‚СЂРѕРІ РџС‘С‚СЂ РџРµС‚СЂРѕРІРёС‡',     '+7-916-100-0002'),
            ('РЎРјРёСЂРЅРѕРІ Р’Р°СЃРёР»РёР№ Р®СЂСЊРµРІРёС‡',  '+7-916-100-0003'),
        ]:
            d, _ = Director.objects.get_or_create(
                full_name=name, defaults={'contact_information': contact}
            )
            directors.append(d)

        accountants = []
        for name, contact in [
            ('РЎРёРґРѕСЂРѕРІР° РђРЅРЅР° РџРµС‚СЂРѕРІРЅР°',   '+7-916-200-0001'),
            ('РљРѕР·Р»РѕРІР° РњР°СЂРёСЏ РРІР°РЅРѕРІРЅР°',   '+7-916-200-0002'),
            ('РћСЂР»РѕРІР° РќР°С‚Р°Р»СЊСЏ РРіРѕСЂРµРІРЅР°',  '+7-916-200-0003'),
        ]:
            a, _ = Accountant.objects.get_or_create(
                full_name=name, defaults={'contact_information': contact}
            )
            accountants.append(a)

        managers = []
        for name, contact in [
            ('РќРѕРІРёРєРѕРІ РђР»РµРєСЃРµР№ РЎРµСЂРіРµРµРІРёС‡', '+7-916-300-0001'),
            ('РњРѕСЂРѕР·РѕРІР° Р•Р»РµРЅР° Р’РёРєС‚РѕСЂРѕРІРЅР°', '+7-916-300-0002'),
            ('Р‘РµР»РѕРІ РљРёСЂРёР»Р» РђРЅРґСЂРµРµРІРёС‡',   '+7-916-300-0003'),
            ('Р—Р°Р№С†РµРІР° РћРєСЃР°РЅР° Р РѕРјР°РЅРѕРІРЅР°', '+7-916-300-0004'),
        ]:
            m, _ = Manager.objects.get_or_create(
                full_name=name, defaults={'contact_information': contact}
            )
            managers.append(m)

        storekeepers = []
        for name, contact in [
            ('РљСѓР·РЅРµС†РѕРІ Р”РјРёС‚СЂРёР№ РћР»РµРіРѕРІРёС‡', '+7-916-400-0001'),
            ('Р’РѕР»РєРѕРІ РђРЅРґСЂРµР№ РќРёРєРѕР»Р°РµРІРёС‡',  '+7-916-400-0002'),
            ('РўРёС…РѕРЅРѕРІ Р•РІРіРµРЅРёР№ РњРёС…Р°Р№Р»РѕРІРёС‡','+7-916-400-0003'),
        ]:
            s, _ = Storekeeper.objects.get_or_create(
                full_name=name, defaults={'contact_information': contact}
            )
            storekeepers.append(s)
        self.stdout.write(self.style.SUCCESS(
            f'  OK вЂ” {len(directors)} РґРёСЂРµРєС‚РѕСЂР°, {len(accountants)} Р±СѓС…РіР°Р»С‚РµСЂР°, '
            f'{len(managers)} РјРµРЅРµРґР¶РµСЂР°, {len(storekeepers)} РєР»Р°РґРѕРІС‰РёРєР°'
        ))

        # в”Ђв”Ђ 3. РџРѕСЃС‚Р°РІС‰РёРєРё в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        self.stdout.write('РџРѕСЃС‚Р°РІС‰РёРєРё...')
        suppliers_raw = [
            ('РћРћРћ РЎС‚СЂРѕР№РњР°С‚РµСЂРёР°Р»',      '7701234567', 'Р—Р°Р№С†РµРІ Рљ.Р’.',    'Р РѕРјР°РЅРѕРІ Рђ.Р”.',   'СЂ/СЃ 40702810100000000001, Р‘РРљ 044525001', 'active'),
            ('Р—РђРћ РњРµС‚Р°Р»Р»РўРѕСЂРі',         '7709876543', 'Р›РµР±РµРґРµРІ Рћ.Рџ.',   'РЎРµРјС‘РЅРѕРІ Р“.Р’.',   'СЂ/СЃ 40702810100000000002, Р‘РРљ 044525002', 'active'),
            ('РћРћРћ Р›РµСЃРѕРїСЂРѕРјРЎРµСЂРІРёСЃ',     '7723456789', 'РџРѕРїРѕРІР° Р•.Р’.',    'Р“СЂРёРіРѕСЂСЊРµРІ Р”.РЎ.', 'СЂ/СЃ 40702810100000000003, Р‘РРљ 044525003', 'active'),
            ('РРџ Р’РѕСЂРѕР±СЊС‘РІ РЎ.Рђ.',       '771122334',  'Р’РѕСЂРѕР±СЊС‘РІ РЎ.Рђ.',  'Р’РѕСЂРѕР±СЊС‘РІ РЎ.Рђ.',  'СЂ/СЃ 40802810100000000004, Р‘РРљ 044525004', 'approved'),
            ('РћРћРћ РЎС‚СЂРѕР№РРЅРІРµСЃС‚ Р“СЂСѓРїРї',  '7756789012', 'РўР°СЂР°СЃРѕРІ Р’.Рќ.',   'Р¤РµРґРѕСЂРѕРІ Рђ.Рџ.',   'СЂ/СЃ 40702810100000000005, Р‘РРљ 044525005', 'approved'),
            ('Р—РђРћ РљР°РјРµРЅСЊРЎС‚СЂРѕР№',        '7734567890', 'РњРёС…Р°Р№Р»РѕРІ РЎ.Р•.',  'РР»СЊРёРЅ Р .Рђ.',     'СЂ/СЃ 40702810100000000006, Р‘РРљ 044525006', 'pending'),
        ]
        suppliers = []
        for name, tax_id, acc_fn, dir_fn, details, st in suppliers_raw:
            sup, _ = Supplier.objects.get_or_create(tax_id=tax_id, defaults={
                'name': name, 'accounted_full_name': acc_fn,
                'director_full_name': dir_fn, 'payment_details': details, 'status': st
            })
            suppliers.append(sup)
        self.stdout.write(self.style.SUCCESS(f'  OK вЂ” {len(suppliers)} РїРѕСЃС‚Р°РІС‰РёРєРѕРІ'))

        # в”Ђв”Ђ 4. РњР°С‚РµСЂРёР°Р»С‹ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        self.stdout.write('РњР°С‚РµСЂРёР°Р»С‹...')
        materials_raw = [
            ('Р¦РµРјРµРЅС‚ Рњ400',        'РјРµС€.',  'РџРѕСЂС‚Р»Р°РЅРґС†РµРјРµРЅС‚ РјР°СЂРєРё Рњ400, РјРµС€РєРё РїРѕ 50 РєРі'),
            ('Р¦РµРјРµРЅС‚ Рњ500',        'РјРµС€.',  'РџРѕСЂС‚Р»Р°РЅРґС†РµРјРµРЅС‚ РјР°СЂРєРё Рњ500, РјРµС€РєРё РїРѕ 50 РєРі'),
            ('РљРёСЂРїРёС‡ РєСЂР°СЃРЅС‹Р№',     'С€С‚.',   'РљРµСЂР°РјРёС‡РµСЃРєРёР№ РїРѕР»РЅРѕС‚РµР»С‹Р№ РєРёСЂРїРёС‡ 250x120x65 РјРј'),
            ('РљРёСЂРїРёС‡ СЃРёР»РёРєР°С‚РЅС‹Р№',  'С€С‚.',   'РЎРёР»РёРєР°С‚РЅС‹Р№ РєРёСЂРїРёС‡ Рњ150, 250x120x65 РјРј'),
            ('РђСЂРјР°С‚СѓСЂР° Г12',       'Рї.Рј.',  'РЎС‚Р°Р»СЊРЅР°СЏ СЂРёС„Р»РµРЅР°СЏ Р°СЂРјР°С‚СѓСЂР° РґРёР°РјРµС‚СЂРѕРј 12 РјРј, Рђ500РЎ'),
            ('РђСЂРјР°С‚СѓСЂР° Г16',       'Рї.Рј.',  'РЎС‚Р°Р»СЊРЅР°СЏ СЂРёС„Р»РµРЅР°СЏ Р°СЂРјР°С‚СѓСЂР° РґРёР°РјРµС‚СЂРѕРј 16 РјРј, Рђ500РЎ'),
            ('Р”РѕСЃРєР° РѕР±СЂРµР·РЅР°СЏ',     'РјВі',    'РҐРІРѕР№РЅР°СЏ РѕР±СЂРµР·РЅР°СЏ РґРѕСЃРєР° 50x150 РјРј, СЃРѕСЂС‚ 2'),
            ('Р‘СЂСѓСЃ СЃС‚СЂРѕРёС‚РµР»СЊРЅС‹Р№',  'РјВі',    'РҐРІРѕР№РЅС‹Р№ СЃС‚СЂРѕРёС‚РµР»СЊРЅС‹Р№ Р±СЂСѓСЃ 100x100 РјРј, СЃРѕСЂС‚ 1'),
            ('РџРµСЃРѕРє СЂРµС‡РЅРѕР№',       'С‚',     'РЎС‚СЂРѕРёС‚РµР»СЊРЅС‹Р№ РјС‹С‚С‹Р№ СЂРµС‡РЅРѕР№ РїРµСЃРѕРє, РјРѕРґСѓР»СЊ РєСЂСѓРїРЅРѕСЃС‚Рё 2.0'),
            ('Р©РµР±РµРЅСЊ С„СЂР°РєС†РёСЏ 20',  'С‚',     'Р“СЂР°РЅРёС‚РЅС‹Р№ С‰РµР±РµРЅСЊ С„СЂР°РєС†РёРё 20-40 РјРј'),
            ('РџРµРЅРѕРїРѕР»РёСЃС‚РёСЂРѕР» 50',  'РјВІ',    'РЈС‚РµРїР»РёС‚РµР»СЊ РїРµРЅРѕРїРѕР»РёСЃС‚РёСЂРѕР» РџРЎР‘-РЎ 50 РјРј, РїР»РѕС‚РЅРѕСЃС‚СЊ 25 РєРі/РјВі'),
            ('Р СѓР±РµСЂРѕРёРґ Р РљРџ-350',   'СЂСѓР».',  'Р СѓР±РµСЂРѕРёРґ РєСЂРѕРІРµР»СЊРЅС‹Р№ СЃ РїРѕСЃС‹РїРєРѕР№, СЂСѓР»РѕРЅ 15 РјВІ'),
        ]
        materials = []
        for name, unit, desc in materials_raw:
            mat, _ = Materials.objects.get_or_create(name=name, defaults={
                'unit_of_measurement': unit, 'description': desc
            })
            materials.append(mat)
        self.stdout.write(self.style.SUCCESS(f'  OK вЂ” {len(materials)} РјР°С‚РµСЂРёР°Р»РѕРІ'))

        # в”Ђв”Ђ 5. Р¦РµРЅС‹ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        self.stdout.write('Р¦РµРЅС‹...')
        # РќРµСЃРєРѕР»СЊРєРѕ РёСЃС‚РѕСЂРёС‡РµСЃРєРёС… С†РµРЅ + С‚РµРєСѓС‰Р°СЏ
        price_dates = [
            today - datetime.timedelta(days=90),
            today - datetime.timedelta(days=30),
            today,
        ]
        prices_raw = [
            # (РјР°С‚РµСЂРёР°Р», РїРѕСЃС‚Р°РІС‰РёРє, [С†РµРЅС‹ РїРѕ РґР°С‚Р°Рј])
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
        self.stdout.write(self.style.SUCCESS(f'  OK вЂ” {price_count} Р·Р°РїРёСЃРµР№ С†РµРЅ'))

        # в”Ђв”Ђ 6. РЎРєР»Р°РґС‹ Рё РЅР°Р·РЅР°С‡РµРЅРёСЏ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        self.stdout.write('РЎРєР»Р°РґС‹...')
        warehouses = []
        for name, address in [
            ('РЎРєР»Р°Рґ в„–1 (Р“Р»Р°РІРЅС‹Р№)',    'Рі. РњРѕСЃРєРІР°, СѓР». РЎРєР»Р°РґСЃРєР°СЏ, Рґ. 1'),
            ('РЎРєР»Р°Рґ в„–2 (РњР°С‚РµСЂРёР°Р»С‹)',  'Рі. РњРѕСЃРєРІР°, СѓР». РџСЂРѕРјС‹С€Р»РµРЅРЅР°СЏ, Рґ. 5'),
            ('РЎРєР»Р°Рґ в„–3 (Р РµР·РµСЂРІРЅС‹Р№)',  'Рі. РџРѕРґРѕР»СЊСЃРє, СѓР». Р—Р°РІРѕРґСЃРєР°СЏ, Рґ. 12'),
        ]:
            wh, _ = Warehouse.objects.get_or_create(
                name=name, defaults={'address': address}
            )
            warehouses.append(wh)

        # РџСЂРёРІСЏР·РєР° РєР»Р°РґРѕРІС‰РёРєРѕРІ Рє СЃРєР»Р°РґР°Рј
        for sk, wh in [
            (storekeepers[0], warehouses[0]),
            (storekeepers[1], warehouses[1]),
            (storekeepers[2], warehouses[2]),
        ]:
            Works.objects.get_or_create(id_storekeeper=sk, id_warehouse=wh)

        # РќР°С‡Р°Р»СЊРЅС‹Рµ РѕСЃС‚Р°С‚РєРё
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
            f'  OK вЂ” {len(warehouses)} СЃРєР»Р°РґР°, {len(inventory_raw)} РїРѕР·РёС†РёР№ РѕСЃС‚Р°С‚РєРѕРІ'
        ))

        # в”Ђв”Ђ 7. РљРѕРЅС‚СЂР°РєС‚С‹ Рё РґРѕРіРѕРІРѕСЂС‹ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        self.stdout.write('РљРѕРЅС‚СЂР°РєС‚С‹ Рё РґРѕРіРѕРІРѕСЂС‹...')

        # РЎРѕР·РґР°С‘Рј 8 РєРѕРЅС‚СЂР°РєС‚РѕРІ СЃ СЂР°Р·РЅС‹РјРё СЃС‚Р°С‚СѓСЃР°РјРё
        contract_statuses = ['signed', 'signed', 'signed', 'approved', 'approved', 'created', 'annulled', 'annulled']
        contracts = []
        for st in contract_statuses:
            c = Contract.objects.create(status=st)
            contracts.append(c)

        # Р—Р°РєР»СЋС‡С‘РЅРЅС‹Рµ РґРѕРіРѕРІРѕСЂС‹ РґР»СЏ 6 РёР· 8 РєРѕРЅС‚СЂР°РєС‚РѕРІ
        concluded_raw = [
            # (contract, supplier, accountant, manager, director, days_ago_concluded, days_payment, cost)
            (contracts[0], suppliers[0], accountants[0], managers[0], directors[0], 60,  30,  1_250_000.00),
            (contracts[1], suppliers[1], accountants[1], managers[1], directors[1], 45,  15,    780_000.00),
            (contracts[2], suppliers[2], accountants[2], managers[2], directors[2], 30,  60,    450_000.00),
            (contracts[3], suppliers[0], accountants[0], managers[3], directors[0], 10,  45,    320_000.00),
            (contracts[6], suppliers[4], accountants[1], managers[0], directors[1], 120, -10,   960_000.00),  # РїСЂРѕСЃСЂРѕС‡РµРЅ
            (contracts[7], suppliers[3], accountants[2], managers[1], directors[2], 180, -30, 2_100_000.00),  # Р·Р°РєСЂС‹С‚
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

        # РњР°С‚РµСЂРёР°Р»С‹ РІ РґРѕРіРѕРІРѕСЂР°С…
        mic_raw = [
            (contracts[0], materials[0],  500.0, 500.0,  'РћС‚Р»РёС‡РЅРѕРµ'),
            (contracts[0], materials[2],  5000.0, 4800.0,'РҐРѕСЂРѕС€РµРµ'),
            (contracts[0], materials[4],  200.0, 200.0,  'РҐРѕСЂРѕС€РµРµ'),
            (contracts[1], materials[5],  100.0, 95.0,   'РҐРѕСЂРѕС€РµРµ'),
            (contracts[1], materials[6],  20.0,  18.0,   'РЈРґРѕРІР»РµС‚РІРѕСЂРёС‚РµР»СЊРЅРѕРµ'),
            (contracts[2], materials[8],  80.0,  80.0,   'РҐРѕСЂРѕС€РµРµ'),
            (contracts[2], materials[9],  50.0,  45.0,   'РҐРѕСЂРѕС€РµРµ'),
            (contracts[3], materials[1],  300.0, 0.0,    'РќРµ РїСЂРёРЅСЏС‚Рѕ'),
            (contracts[3], materials[3],  2000.0, 0.0,   'РќРµ РїСЂРёРЅСЏС‚Рѕ'),
            (contracts[6], materials[10], 1000.0, 1000.0,'РћС‚Р»РёС‡РЅРѕРµ'),
            (contracts[6], materials[11], 500.0, 500.0,  'РҐРѕСЂРѕС€РµРµ'),
            (contracts[7], materials[7],  40.0,  40.0,   'РҐРѕСЂРѕС€РµРµ'),
        ]
        for contract, mat, qty_plan, qty_actual, cond in mic_raw:
            MaterialsInContract.objects.get_or_create(
                id_contract=contract, id_materials=mat,
                defaults={'materials_quality_in_contract': qty_plan,
                          'actual_quantity': qty_actual, 'condition': cond}
            )
        self.stdout.write(self.style.SUCCESS(
            f'  OK вЂ” {len(contracts)} РєРѕРЅС‚СЂР°РєС‚РѕРІ, {len(concluded_list)} Р·Р°РєР»СЋС‡С‘РЅРЅС‹С…, '
            f'{len(mic_raw)} РїРѕР·РёС†РёР№ РјР°С‚РµСЂРёР°Р»РѕРІ'
        ))

        # в”Ђв”Ђ 8. РђРєС‚С‹ РїСЂРёР±С‹С‚РёСЏ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        self.stdout.write('РџРѕСЃС‚Р°РІРєРё Рё Р°РєС‚С‹ РїСЂРёР±С‹С‚РёСЏ...')

        acts_data = [
            DeliveryStatus.RECEIVED,   # act 1 вЂ” РїСЂРёРЅСЏС‚Рѕ
            DeliveryStatus.DELIVERED,  # act 2 вЂ” РґРѕСЃС‚Р°РІР»РµРЅРѕ, РѕР¶РёРґР°РµС‚ РїСЂРёС‘РјРєРё
            DeliveryStatus.DELIVERED,  # act 3
            DeliveryStatus.PENDING,    # act 4 вЂ” РµС‰С‘ РµРґРµС‚
            DeliveryStatus.PENDING,    # act 5
            DeliveryStatus.PENDING,    # act 6 вЂ” Р·Р°РґРµСЂР¶РєР°
        ]
        acts = []
        for st in acts_data:
            act = ActOfArrival.objects.create(status=st)
            acts.append(act)

        # РџРѕСЃС‚Р°РІРєРё
        deliveries_raw = [
            # (contract, status, days_delta, act)
            (contracts[0], DeliveryStatus.RECEIVED,     -55, acts[0]),
            (contracts[1], DeliveryStatus.DELIVERED,    -3,  acts[1]),
            (contracts[2], DeliveryStatus.IN_TRANSIT,   +2,  acts[2]),
            (contracts[3], DeliveryStatus.PENDING,      +5,  acts[3]),
            (contracts[6], DeliveryStatus.DELIVERED,    -115,acts[4]),
            (contracts[7], DeliveryStatus.DELAYED,      -10, acts[5]),  # Р·Р°РґРµСЂР¶Р°РЅР°
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

        # РџСЂРёС‘РјРєР° РґР»СЏ РїРµСЂРІРѕР№ РїРѕСЃС‚Р°РІРєРё (СЃ auto-РѕР±РЅРѕРІР»РµРЅРёРµРј СЃРєР»Р°РґР°)
        AcceptanceOfDelivery.objects.get_or_create(
            id_storekeeper=storekeepers[0],
            id_act_of_arrival=acts[0],
        )
        self.stdout.write(self.style.SUCCESS(
            f'  OK вЂ” {len(acts)} Р°РєС‚РѕРІ РїСЂРёР±С‹С‚РёСЏ, {len(deliveries)} РїРѕСЃС‚Р°РІРѕРє, 1 РїСЂРёС‘РјРєР°'
        ))

        # в”Ђв”Ђ РС‚РѕРі в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('OK! РўРµСЃС‚РѕРІС‹Рµ РґР°РЅРЅС‹Рµ СѓСЃРїРµС€РЅРѕ Р·Р°РіСЂСѓР¶РµРЅС‹!'))
        self.stdout.write('')
        self.stdout.write('РЈС‡С‘С‚РЅС‹Рµ Р·Р°РїРёСЃРё (РїР°СЂРѕР»СЊ Сѓ РІСЃРµС…: TestPass123!):')
        self.stdout.write('  admin        вЂ” СЃСѓРїРµСЂРїРѕР»СЊР·РѕРІР°С‚РµР»СЊ (Django admin)')
        self.stdout.write('  manager1/2   вЂ” РјРµРЅРµРґР¶РµСЂ')
        self.stdout.write('  accountant1/2вЂ” Р±СѓС…РіР°Р»С‚РµСЂ')
        self.stdout.write('  storekeeper1/2/3 вЂ” РєР»Р°РґРѕРІС‰РёРє')
        self.stdout.write('  director1    вЂ” РґРёСЂРµРєС‚РѕСЂ')
        self.stdout.write('  viewer1      вЂ” РїСЂРѕСЃРјРѕС‚СЂ (С‚РѕР»СЊРєРѕ С‡С‚РµРЅРёРµ)')
        self.stdout.write('')
        self.stdout.write('Swagger: http://localhost:8000/api/docs/')

