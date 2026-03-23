"""Автотесты для приложения contracts.
Запуск: python manage.py test contracts --settings=config.test_settings -v 2
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
from partners.models import Supplier
from personnel.models import Accountant, Director, Manager
from users.models import UserProfile


def make_user(username='tester', role='admin'):
    user = User.objects.create_user(username=username, password='x', is_active=True)
    UserProfile.objects.create(user=user, role=role)
    return user


def make_contract(st=Contract.STATUS_CREATED):
    return Contract.objects.create(status=st)


def make_supplier():
    return Supplier.objects.create(
        name='Тест',
        tax_id=f'0000000{Supplier.objects.count() + 1}',
        accounted_full_name='А.А.',
        director_full_name='Б.Б.',
        payment_details='р/с 0',
        status='active',
    )


def make_staff():
    acc = Accountant.objects.create(full_name='Бух', contact_information='+7')
    mgr = Manager.objects.create(full_name='Менеджер', contact_information='+7')
    dr = Director.objects.create(full_name='Директор', contact_information='+7')
    return acc, mgr, dr


class ContractStatusFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.contract = make_contract()

    def _url(self):
        return f'/api/contracts/{self.contract.id_contract}/set-status/'

    def test_default_status_created(self):
        resp = self.client.post('/api/contracts/', {})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], Contract.STATUS_CREATED)

    def test_allowed_transition_created_to_approved(self):
        resp = self.client.post(self._url(), {'status': Contract.STATUS_APPROVED})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], Contract.STATUS_APPROVED)
        self.assertEqual(resp.data['available_next_statuses'], [Contract.STATUS_SIGNED])

    def test_forbidden_transition_created_to_signed(self):
        resp = self.client.post(self._url(), {'status': Contract.STATUS_SIGNED})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_full_transition_chain(self):
        for target in (Contract.STATUS_APPROVED, Contract.STATUS_SIGNED, Contract.STATUS_ANNULLED):
            resp = self.client.post(self._url(), {'status': target})
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.STATUS_ANNULLED)


class MaterialsAutoPriceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

        self.contract = make_contract(Contract.STATUS_SIGNED)
        self.supplier = make_supplier()
        acc, mgr, dr = make_staff()
        Concluded.objects.create(
            id_contract=self.contract,
            id_supplier=self.supplier,
            id_accountant=acc,
            id_manager=mgr,
            id_director=dr,
            conclusion_dates=timezone.now().date(),
            payment_date=timezone.now().date() + datetime.timedelta(days=7),
            delivery_date=timezone.now().date() + datetime.timedelta(days=10),
            cost=0,
        )
        self.material = Materials.objects.create(
            name='Цемент М500',
            unit_of_measurement='шт',
            description='desc',
        )

    def test_autofill_supplier_price(self):
        Prices.objects.create(
            id_materials=self.material,
            id_supplier=self.supplier,
            effective_dates=timezone.now().date(),
            price=125.5,
        )
        resp = self.client.post('/api/contracts/materials/', {
            'id_contract': self.contract.id_contract,
            'id_materials': self.material.id_materials,
            'materials_quality_in_contract': 10,
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(resp.data['unit_price']), 125.5)

    def test_reject_material_without_supplier_price(self):
        other_supplier = make_supplier()
        Prices.objects.create(
            id_materials=self.material,
            id_supplier=other_supplier,
            effective_dates=timezone.now().date() - datetime.timedelta(days=2),
            price=110.0,
        )

        resp = self.client.post('/api/contracts/materials/', {
            'id_contract': self.contract.id_contract,
            'id_materials': self.material.id_materials,
            'materials_quality_in_contract': 5,
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('id_materials', resp.data)

    def test_error_when_price_missing(self):
        resp = self.client.post('/api/contracts/materials/', {
            'id_contract': self.contract.id_contract,
            'id_materials': self.material.id_materials,
            'materials_quality_in_contract': 5,
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('unit_price' in resp.data or 'id_materials' in resp.data)


class ContractPdfGenerationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    @patch('contracts.api.v1.views.generate_contract_pdf')
    def test_generate_pdf_on_contract_create(self, mock_generate_pdf):
        mock_generate_pdf.return_value = type('Gen', (), {
            'relative_path': 'contracts_docs/mock_contract.pdf'
        })()

        resp = self.client.post('/api/contracts/', {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        contract = Contract.objects.get(id_contract=resp.data['id_contract'])
        self.assertEqual(contract.file_path, 'contracts_docs/mock_contract.pdf')
        mock_generate_pdf.assert_called_once()

    @patch('contracts.api.v1.views.generate_contract_pdf')
    def test_generate_pdf_on_contract_update(self, mock_generate_pdf):
        mock_generate_pdf.return_value = type('Gen', (), {
            'relative_path': 'contracts_docs/mock_contract_updated.pdf'
        })()
        contract = make_contract()

        resp = self.client.patch(f'/api/contracts/{contract.id_contract}/', {'status': Contract.STATUS_CREATED}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        contract.refresh_from_db()
        self.assertEqual(contract.file_path, 'contracts_docs/mock_contract_updated.pdf')
        mock_generate_pdf.assert_called_once()

    @patch('contracts.api.v1.views.DocxTemplate')
    @patch('contracts.api.v1.views.Path.exists', return_value=True)
    def test_generate_docx_normalizes_camelcase_payload_keys(self, _mock_exists, mock_docx_template):
        doc_instance = mock_docx_template.return_value
        doc_instance.render.return_value = None
        doc_instance.save.return_value = None

        payload = {
            'template': 'supply_contract_template.docx',
            'data': {
                'contractNumber': '123',
                'supplierName': 'ТестПоставщик',
                'items': [{'qtyActual': 5}],
            },
        }
        response = self.client.post('/api/contracts/documents/generate-docx/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        args, _kwargs = doc_instance.render.call_args
        rendered_context = args[0]
        self.assertIn('contract_number', rendered_context)
        self.assertIn('supplier_name', rendered_context)
        self.assertEqual(rendered_context['items'][0]['qty_actual'], 5)


class CatalogMaterialsBySupplierTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.supplier = make_supplier()
        self.other_supplier = make_supplier()
        self.material_for_supplier = Materials.objects.create(
            name='Песок',
            unit_of_measurement='кг',
            description='desc',
        )
        self.material_other = Materials.objects.create(
            name='Щебень',
            unit_of_measurement='кг',
            description='desc',
        )
        Prices.objects.create(
            id_materials=self.material_for_supplier,
            id_supplier=self.supplier,
            effective_dates=timezone.now().date(),
            price=10,
        )
        Prices.objects.create(
            id_materials=self.material_other,
            id_supplier=self.other_supplier,
            effective_dates=timezone.now().date(),
            price=20,
        )

    def test_materials_filtered_by_supplier(self):
        resp = self.client.get(f'/api/catalog/materials/by_supplier/?supplier_id={self.supplier.id_supplier}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {item['id_materials'] for item in resp.data}
        self.assertIn(self.material_for_supplier.id_materials, ids)
        self.assertNotIn(self.material_other.id_materials, ids)
