import django
import os

# Укажите правильное имя вашего проекта
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction

from personnel.models import Accountant, Director, Manager, Storekeeper
from warehousing.models import Warehouse, Inventory, Works
from partners.models import Supplier
from catalog.models import Materials, Prices
from contracts.models import Contract, Concluded, MaterialsInContract
from deliveries.models import ActOfArrival, Delivery, AcceptanceOfDelivery
from deliveries.choices import DeliveryStatus


@transaction.atomic
def create_test_data():
    print("Creating test data...")

    # --- Accountants (3) ---
    accountants = [
        Accountant.objects.get_or_create(
            full_name="Петрова Петровна Петрова",
            contact_information="petrova@example.com"
        )[0],
        Accountant.objects.get_or_create(
            full_name="Сидоров Сидор Сидорович",
            contact_information="sidorov@example.com"
        )[0],
        Accountant.objects.get_or_create(
            full_name="Иванов Иван Иванович",
            contact_information="ivanov@example.com"
        )[0],
    ]

    # --- Directors (3) ---
    directors = [
        Director.objects.get_or_create(
            full_name="Смирнов Смирн Смирнович",
            contact_information="smirnov@example.com"
        )[0],
        Director.objects.get_or_create(
            full_name="Кузнецова Кузнецова Кузнецова",
            contact_information="kuznetsova@example.com"
        )[0],
        Director.objects.get_or_create(
            full_name="Волков Волков Волкович",
            contact_information="volkov@example.com"
        )[0],
    ]

    # --- Managers (3) ---
    managers = [
        Manager.objects.get_or_create(
            full_name="Соколов Соколов Соколович",
            contact_information="sokolov@example.com"
        )[0],
        Manager.objects.get_or_create(
            full_name="Козлов Козел Козлович",
            contact_information="kozlov@example.com"
        )[0],
        Manager.objects.get_or_create(
            full_name="Морозов Мороз Морозович",
            contact_information="morozov@example.com"
        )[0],
    ]

    # --- Storekeepers (3) ---
    storekeepers = [
        Storekeeper.objects.get_or_create(
            full_name="Попова Попова Поповна",
            contact_information="popova@example.com"
        )[0],
        Storekeeper.objects.get_or_create(
            full_name="Лебедев Лебедев Лебедевич",
            contact_information="lebedev@example.com"
        )[0],
        Storekeeper.objects.get_or_create(
            full_name="Соколова Соколова Соколовна",
            contact_information="sokolova_store@example.com"
        )[0],
    ]

    # --- Warehouses (3) ---
    warehouses = [
        Warehouse.objects.get_or_create(
            name="Основной склад",
            address="ул. Примерная, д. 1"
        )[0],
        Warehouse.objects.get_or_create(
            name="Вторичный склад",
            address="ул. Вторичная, д. 2"
        )[0],
        Warehouse.objects.get_or_create(
            name="Резервный склад",
            address="ул. Резервная, д. 3"
        )[0],
    ]

    # --- Suppliers (3) ---
    suppliers = [
        Supplier.objects.get_or_create(
            name="ООО Ромашка",
            tax_id="1234567890",
            accounted_full_name="Иванов Иван Иванович",
            director_full_name="Петров Петр Петрович",
            payment_details="Расчетный счет: 40817810123456789012"
        )[0],
        Supplier.objects.get_or_create(
            name="ЗАО Василек",
            tax_id="0987654321",
            accounted_full_name="Сидоров Сидор Сидорович",
            director_full_name="Смирнов Смирн Смирнович",
            payment_details="Расчетный счет: 40817810987654321098"
        )[0],
        Supplier.objects.get_or_create(
            name="ООО Лилия",
            tax_id="1122334455",
            accounted_full_name="Петрова Петровна Петрова",
            director_full_name="Кузнецова Кузнецова Кузнецова",
            payment_details="Расчетный счет: 40817810112233445566"
        )[0],
    ]

    # --- Materials (5) ---
    materials = [
        Materials.objects.get_or_create(
            name="Цемент М500",
            unit_of_measurement="тонна",
            description="Высококачественный цемент для строительных работ"
        )[0],
        Materials.objects.get_or_create(
            name="Песок строительный",
            unit_of_measurement="кубический метр",
            description="Чистый строительный песок для различных целей"
        )[0],
        Materials.objects.get_or_create(
            name="Щебень фракция 20-40 мм",
            unit_of_measurement="тонна",
            description="Крупный щебень для дорожного строительства"
        )[0],
        Materials.objects.get_or_create(
            name="Арматура A500C",
            unit_of_measurement="тонна",
            description="Высокопрочная арматура для железобетонных конструкций"
        )[0],
        Materials.objects.get_or_create(
            name="Гравий фракция 5-20 мм",
            unit_of_measurement="тонна",
            description="Гравий для дорожного строительства и ландшафтного дизайна"
        )[0],
    ]

    # --- Contracts (5) ---
    contracts = [
        Contract.objects.get_or_create(id_contract=1)[0],
        Contract.objects.get_or_create(id_contract=2)[0],
        Contract.objects.get_or_create(id_contract=3)[0],
        Contract.objects.get_or_create(id_contract=4)[0],
        Contract.objects.get_or_create(id_contract=5)[0],
    ]

    # --- Acts of Arrival (4) ---
    acts = [
        ActOfArrival.objects.get_or_create(status=DeliveryStatus.DELIVERED)[0],
        ActOfArrival.objects.get_or_create(status=DeliveryStatus.NOT_DELIVERED)[0],
        ActOfArrival.objects.get_or_create(status=DeliveryStatus.CANCEL)[0],
        ActOfArrival.objects.get_or_create(status=DeliveryStatus.DELIVERED)[0],
    ]

    # --- Deliveries (4) ---
    deliveries = [
        Delivery.objects.get_or_create(
            status=DeliveryStatus.DELIVERED,
            delivery_date="2024-01-15",
            id_contract=contracts[0],
            id_act_of_arrival=acts[0]
        )[0],
        Delivery.objects.get_or_create(
            status=DeliveryStatus.NOT_DELIVERED,
            delivery_date="2024-02-20",
            id_contract=contracts[1],
            id_act_of_arrival=acts[1]
        )[0],
        Delivery.objects.get_or_create(
            status=DeliveryStatus.CANCEL,
            delivery_date="2024-03-10",
            id_contract=contracts[2],
            id_act_of_arrival=acts[2]
        )[0],
        Delivery.objects.get_or_create(
            status=DeliveryStatus.DELIVERED,
            delivery_date="2024-04-05",
            id_contract=contracts[3],
            id_act_of_arrival=acts[3]
        )[0],
    ]

    # --- Prices (4) ---
    prices = [
        Prices.objects.get_or_create(
            effective_dates="2024-01-01",
            price=100.0,
            id_materials=materials[0],
            id_supplier=suppliers[0]
        )[0],
        Prices.objects.get_or_create(
            effective_dates="2024-01-01",
            price=50.0,
            id_materials=materials[1],
            id_supplier=suppliers[1]
        )[0],
        Prices.objects.get_or_create(
            effective_dates="2024-01-01",
            price=80.0,
            id_materials=materials[2],
            id_supplier=suppliers[2]
        )[0],
        Prices.objects.get_or_create(
            effective_dates="2024-01-01",
            price=200.0,
            id_materials=materials[3],
            id_supplier=suppliers[0]  # вместо несуществующего suppliers[3]
        )[0],
    ]

    # --- Inventory (5) ---
    inventory_items = [
        Inventory.objects.get_or_create(
            quantity=100,
            id_warehouse=warehouses[0],
            id_materials=materials[0]
        )[0],
        Inventory.objects.get_or_create(
            quantity=200,
            id_warehouse=warehouses[0],
            id_materials=materials[1]
        )[0],
        Inventory.objects.get_or_create(
            quantity=150,
            id_warehouse=warehouses[1],
            id_materials=materials[2]
        )[0],
        Inventory.objects.get_or_create(
            quantity=50,
            id_warehouse=warehouses[1],
            id_materials=materials[3]
        )[0],
        Inventory.objects.get_or_create(
            quantity=300,
            id_warehouse=warehouses[2],
            id_materials=materials[4]
        )[0],
    ]

    # --- Works (4) ---
    works = [
        Works.objects.get_or_create(
            id_storekeeper=storekeepers[0],
            id_warehouse=warehouses[0]
        )[0],
        Works.objects.get_or_create(
            id_storekeeper=storekeepers[1],
            id_warehouse=warehouses[1]
        )[0],
        Works.objects.get_or_create(
            id_storekeeper=storekeepers[2],
            id_warehouse=warehouses[2]
        )[0],
        Works.objects.get_or_create(
            id_storekeeper=storekeepers[0],
            id_warehouse=warehouses[1]
        )[0],
    ]

    # --- Acceptances (4) ---
    acceptances = [
        AcceptanceOfDelivery.objects.get_or_create(
            id_storekeeper=storekeepers[0],
            id_act_of_arrival=acts[0]
        )[0],
        AcceptanceOfDelivery.objects.get_or_create(
            id_storekeeper=storekeepers[1],
            id_act_of_arrival=acts[1]
        )[0],
        AcceptanceOfDelivery.objects.get_or_create(
            id_storekeeper=storekeepers[2],
            id_act_of_arrival=acts[2]
        )[0],
        AcceptanceOfDelivery.objects.get_or_create(
            id_storekeeper=storekeepers[0],
            id_act_of_arrival=acts[3]
        )[0],
    ]

    # --- Concluded (4) ---
    concluded_list = []
    for i, contract in enumerate(contracts[:4]):
        if not Concluded.objects.filter(id_contract=contract).exists():
            concluded = Concluded.objects.create(
                conclusion_dates=f"2024-01-{10+i:02d}",
                payment_date=f"2024-02-{15+i:02d}",
                cost=100000.0 * (i+1),
                id_supplier=suppliers[i % len(suppliers)],
                id_contract=contract,
                id_accountant=accountants[i % len(accountants)],
                id_manager=managers[i % len(managers)],
                id_director=directors[i % len(directors)]
            )
            concluded_list.append(concluded)
        else:
            concluded_list.append(Concluded.objects.get(id_contract=contract))

    # --- MaterialsInContract (4 договора × 3 материала = 12) ---
    materials_in_contract = []
    for i, contract in enumerate(contracts[:4]):
        for j, material in enumerate(materials[:3]):
            obj, created = MaterialsInContract.objects.get_or_create(
                id_materials=material,
                id_contract=contract,
                defaults={
                    'materials_quality_in_contract': 1.0 + j * 0.1,
                    'condition': 'Новый' if j % 2 == 0 else 'Б/у',
                    'actual_quantity': 100.0 + j * 50
                }
            )
            materials_in_contract.append(obj)

    print("Тестовые данные успешно добавлены (или уже существовали).")
    print(f"Создано/получено объектов: "
          f"Accountant={len(accountants)}, Director={len(directors)}, Manager={len(managers)}, "
          f"Storekeeper={len(storekeepers)}, Warehouse={len(warehouses)}, Supplier={len(suppliers)}, "
          f"Materials={len(materials)}, Contract={len(contracts)}, ActOfArrival={len(acts)}, "
          f"Delivery={len(deliveries)}, Prices={len(prices)}, Inventory={len(inventory_items)}, "
          f"Works={len(works)}, AcceptanceOfDelivery={len(acceptances)}, Concluded={len(concluded_list)}, "
          f"MaterialsInContract={len(materials_in_contract)}")


if __name__ == "__main__":
    create_test_data()
