"""
Автотесты для приложения contracts.
Запуск: python manage.py test contracts -v 2
"""
import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from contracts.models import Contract, Concluded, MaterialsInContract
from partners.models import Supplier
from personnel.models import Director, Accountant, Manager
from catalog.models import Materials
from users.models import UserProfile


def make_user(username='tester', role='admin'):
    user = User.objects.create_user(username=username, password='x', is_active=True)
    UserProfile.objects.create(user=user, role=role)
    return user


def make_contract(st='draft'):
    return Contract.objects.create(status=st)


def make_supplier():
    return Supplier.objects.create(
        name='Тест', tax_id='0000000001',
        accounted_full_name='А.А.', director_full_name='Б.Б.',
        payment_details='р/с 0', status='active'
    )


class ContractCRUDTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/contracts/'

    def test_list_contracts(self):
        make_contract(); make_contract('active')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_create_contract_default_status_draft(self):
        resp = self.client.post(self.url, {})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], 'draft')

    def test_retrieve_contract(self):
        c = make_contract('active')
        resp = self.client.get(f'{self.url}{c.id_contract}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'active')

    def test_delete_contract(self):
        c = make_contract()
        resp = self.client.delete(f'{self.url}{c.id_contract}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class ContractSetStatusTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.contract = make_contract()

    def _url(self):
        return f'/api/contracts/{self.contract.id_contract}/set-status/'

    def test_set_status_review(self):
        resp = self.client.post(self._url(), {'status': 'review'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, 'review')

    def test_set_status_closed(self):
        resp = self.client.post(self._url(), {'status': 'closed'})
        self.assertEqual(resp.data['status'], 'closed')

    def test_set_status_invalid_returns_400(self):
        resp = self.client.post(self._url(), {'status': 'archived'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_status_all_allowed_values(self):
        for st in ('draft', 'review', 'active', 'closed'):
            resp = self.client.post(self._url(), {'status': st})
            self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ConcludedStatisticsTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

        sup = make_supplier()
        acc = Accountant.objects.create(full_name='Бух', contact_information='+7')
        mgr = Manager.objects.create(full_name='Менеджер', contact_information='+7')
        dr = Director.objects.create(full_name='Директор', contact_information='+7')
        today = timezone.now().date()

        for cost, days_ago in [(100000, 5), (200000, 40)]:
            c = make_contract('active')
            Concluded.objects.create(
                id_contract=c, id_supplier=sup, id_accountant=acc,
                id_manager=mgr, id_director=dr,
                conclusion_dates=today - datetime.timedelta(days=days_ago),
                payment_date=today + datetime.timedelta(days=10),
                cost=cost
            )

    def test_statistics_endpoint_returns_counts(self):
        resp = self.client.get('/api/contracts/concluded/statistics/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['total_contracts'], 2)
        self.assertEqual(resp.data['total_cost'], 300000.0)

    def test_statistics_recent_month(self):
        resp = self.client.get('/api/contracts/concluded/statistics/')
        self.assertEqual(resp.data['recent_contracts_month'], 1)

    def test_by_manager_endpoint(self):
        resp = self.client.get('/api/contracts/concluded/by_manager/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(resp.data), 0)
        self.assertIn('manager_name', resp.data[0])
        self.assertIn('total_cost', resp.data[0])
