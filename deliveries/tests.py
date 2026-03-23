"""Автотесты для приложения deliveries.
Запуск: python manage.py test deliveries --settings=config.test_settings -v 2
"""

import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import Materials, Prices
from contracts.models import Concluded, Contract, MaterialsInContract
from deliveries.choices import DeliveryStatus
from deliveries.models import ActOfArrival, Delivery
from partners.models import Supplier
from personnel.models import Accountant, Director, Manager, Storekeeper
from users.models import UserProfile
from warehousing.models import Warehouse, Works


def make_user(username='tester', role='admin'):
    user = User.objects.create_user(username=username, password='x', is_active=True)
    UserProfile.objects.create(user=user, role=role)
    return user


def make_supplier():
    return Supplier.objects.create(
        name='Поставщик Тест',
        tax_id=f'1000000{Supplier.objects.count() + 1}',
        accounted_full_name='Бухгалтер',
        director_full_name='Директор',
        payment_details='р/с 0',
        status='active',
    )


class ActOfArrivalFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

        self.supplier = make_supplier()
        self.acc = Accountant.objects.create(full_name='Бух', contact_information='+7')
        self.mgr = Manager.objects.create(full_name='Менеджер', contact_information='+7')
        self.dr = Director.objects.create(full_name='Директор', contact_information='+7')
        self.storekeeper = Storekeeper.objects.create(full_name='Кладовщик', contact_information='+7')
        self.warehouse = Warehouse.objects.create(name='Склад', address='Москва')
        Works.objects.create(id_storekeeper=self.storekeeper, id_warehouse=self.warehouse)

        self.material = Materials.objects.create(name='Кирпич', unit_of_measurement='шт', description='desc')
        Prices.objects.create(
            id_materials=self.material,
            id_supplier=self.supplier,
            effective_dates=timezone.now().date(),
            price=15,
        )

    def _create_contract_bundle(self, status_value=Contract.STATUS_SIGNED):
        contract = Contract.objects.create(status=status_value)
        Concluded.objects.create(
            id_contract=contract,
            id_supplier=self.supplier,
            id_accountant=self.acc,
            id_manager=self.mgr,
            id_director=self.dr,
            conclusion_dates=timezone.now().date(),
            payment_date=timezone.now().date() + datetime.timedelta(days=7),
            delivery_date=timezone.now().date() + datetime.timedelta(days=10),
            cost=0,
        )
        MaterialsInContract.objects.create(
            id_contract=contract,
            id_materials=self.material,
            materials_quality_in_contract=100,
            unit_price=15,
        )

        act = ActOfArrival.objects.create(status=DeliveryStatus.PENDING)
        delivery = Delivery.objects.create(
            status=DeliveryStatus.IN_TRANSIT,
            delivery_date=timezone.now().date(),
            id_contract=contract,
            id_act_of_arrival=act,
        )
        return contract, act, delivery

    def test_start_receiving_blocked_if_contract_not_signed(self):
        _, act, _ = self._create_contract_bundle(status_value=Contract.STATUS_APPROVED)
        resp = self.client.post(f'/api/deliveries/acts-of-arrival/{act.id_act_of_arrival}/start_receiving/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_materials_endpoint_returns_required_fields(self):
        _, act, delivery = self._create_contract_bundle(status_value=Contract.STATUS_SIGNED)
        resp = self.client.get(f'/api/deliveries/acts-of-arrival/{act.id_act_of_arrival}/materials/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['delivery_id'], delivery.id_delivery)
        self.assertEqual(len(resp.data['items']), 1)
        item = resp.data['items'][0]
        self.assertIn('contract_quantity', item)
        self.assertIn('actual_quantity', item)
        self.assertIn('condition', item)
        self.assertIn('unit_price', item)

    def test_start_receiving_accepts_storekeeper_and_saves_items(self):
        _, act, delivery = self._create_contract_bundle(status_value=Contract.STATUS_SIGNED)
        payload = {
            'storekeeper_id': self.storekeeper.id_storekeeper,
            'items': [
                {
                    'material_id': self.material.id_materials,
                    'actual_quantity': 95,
                    'condition': 'хорошее',
                }
            ],
        }
        resp = self.client.post(
            f'/api/deliveries/acts-of-arrival/{act.id_act_of_arrival}/start_receiving/',
            payload,
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        act.refresh_from_db()
        self.assertEqual(act.status, DeliveryStatus.RECEIVING)

        mic = MaterialsInContract.objects.get(id_contract=delivery.id_contract, id_materials=self.material)
        self.assertEqual(mic.actual_quantity, 95)
        self.assertEqual(mic.condition, 'хорошее')

    @patch('deliveries.api.v1.views.generate_arrival_pdf')
    @patch('deliveries.api.v1.views.generate_divergence_pdf')
    def test_confirm_acceptance_saves_actual_data_and_generates_divergence_pdf(self, mock_divergence_pdf, mock_arrival_pdf):
        mock_arrival_pdf.return_value = type('Gen', (), {
            'relative_path': 'contracts_docs/arrival_test.pdf',
            'filename': 'arrival_test.pdf',
            'file_url': '/media/contracts_docs/arrival_test.pdf',
        })()
        mock_divergence_pdf.return_value = type('Gen', (), {
            'relative_path': 'contracts_docs/divergence_test.pdf',
            'filename': 'divergence_test.pdf',
            'file_url': '/media/contracts_docs/divergence_test.pdf',
        })()

        _, act, delivery = self._create_contract_bundle(status_value=Contract.STATUS_SIGNED)

        payload = {
            'storekeeper_id': self.storekeeper.id_storekeeper,
            'items': [
                {
                    'material_id': self.material.id_materials,
                    'actual_quantity': 80,
                    'condition': 'Брак',
                }
            ],
        }
        resp = self.client.post(
            f'/api/deliveries/acts-of-arrival/{act.id_act_of_arrival}/confirm_acceptance/',
            payload,
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'accepted')
        self.assertTrue(resp.data['divergence_pdf']['generated'])
        self.assertEqual(resp.data['divergence_items_count'], 1)

        mic = MaterialsInContract.objects.get(id_contract=delivery.id_contract, id_materials=self.material)
        self.assertEqual(mic.actual_quantity, 80)
        self.assertEqual(mic.condition, 'Брак')

        act.refresh_from_db()
        self.assertEqual(act.status, DeliveryStatus.RECEIVED)
        self.assertEqual(act.acceptance_pdf_path, 'contracts_docs/arrival_test.pdf')
        self.assertEqual(act.divergence_pdf_path, 'contracts_docs/divergence_test.pdf')

        mock_arrival_pdf.assert_called_once()
        mock_divergence_pdf.assert_called_once()
