"""
Автотесты для приложения partners (поставщики).
Запуск: python manage.py test partners -v 2
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from partners.models import Supplier
from users.models import UserProfile


def make_user(username='tester', role='admin'):
    user = User.objects.create_user(username=username, password='x', is_active=True)
    UserProfile.objects.create(user=user, role=role)
    return user


def make_supplier(**kwargs):
    defaults = {
        'name': 'ООО Тест',
        'tax_id': '1234567890',
        'accounted_full_name': 'Иванов И.И.',
        'director_full_name': 'Петров П.П.',
        'payment_details': 'р/с 000',
        'status': 'pending',
    }
    defaults.update(kwargs)
    return Supplier.objects.create(**defaults)


class SupplierCRUDTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/partners/suppliers/'

    def test_list_suppliers(self):
        make_supplier(tax_id='111')
        make_supplier(tax_id='222', name='ЗАО Другой')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_create_supplier(self):
        resp = self.client.post(self.url, {
            'name': 'Новый поставщик',
            'tax_id': '9999999999',
            'accounted_full_name': 'Смирнов С.С.',
            'director_full_name': 'Козлов К.К.',
            'payment_details': 'р/с 123',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Supplier.objects.count(), 1)

    def test_create_supplier_default_status_pending(self):
        resp = self.client.post(self.url, {
            'name': 'Поставщик2',
            'tax_id': '8888888888',
            'accounted_full_name': 'А.А.',
            'director_full_name': 'Б.Б.',
            'payment_details': 'р/с 456',
        })
        self.assertEqual(resp.data['status'], 'pending')

    def test_retrieve_supplier(self):
        sup = make_supplier()
        resp = self.client.get(f'{self.url}{sup.id_supplier}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['name'], 'ООО Тест')

    def test_update_supplier(self):
        sup = make_supplier()
        resp = self.client.patch(f'{self.url}{sup.id_supplier}/', {'name': 'Обновлён'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        sup.refresh_from_db()
        self.assertEqual(sup.name, 'Обновлён')

    def test_delete_supplier(self):
        sup = make_supplier()
        resp = self.client.delete(f'{self.url}{sup.id_supplier}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Supplier.objects.count(), 0)


class SupplierSetStatusTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.sup = make_supplier()

    def test_set_status_approved(self):
        url = f'/api/partners/suppliers/{self.sup.id_supplier}/set-status/'
        resp = self.client.post(url, {'status': 'approved'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.sup.refresh_from_db()
        self.assertEqual(self.sup.status, 'approved')

    def test_set_status_active(self):
        url = f'/api/partners/suppliers/{self.sup.id_supplier}/set-status/'
        resp = self.client.post(url, {'status': 'active'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'active')

    def test_set_status_invalid_returns_400(self):
        url = f'/api/partners/suppliers/{self.sup.id_supplier}/set-status/'
        resp = self.client.post(url, {'status': 'deleted'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_status_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        url = f'/api/partners/suppliers/{self.sup.id_supplier}/set-status/'
        resp = self.client.post(url, {'status': 'active'})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
