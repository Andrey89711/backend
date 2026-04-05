from django.contrib.auth import get_user_model
from rest_framework import viewsets
from ...models import Director, Accountant, Manager, Storekeeper
from .serializers import DirectorSerializer, AccountantSerializer, ManagerSerializer, StorekeeperSerializer
from users.permissions import HasAnyRole, ADMIN, DIRECTOR, MANAGER, ACCOUNTANT, STOREKEEPER

User = get_user_model()

_READ_ROLES = (ADMIN, DIRECTOR, MANAGER, ACCOUNTANT, STOREKEEPER)
_WRITE_ROLES = (ADMIN, DIRECTOR, MANAGER)


def _delete_linked_user(instance):
    """Удаляет User, связанный с сотрудником по email."""
    try:
        User.objects.get(email=instance.contact_information).delete()
    except User.DoesNotExist:
        pass


class DirectorViewSet(viewsets.ModelViewSet):
    queryset = Director.objects.all()
    serializer_class = DirectorSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [HasAnyRole(*_READ_ROLES)()]
        return [HasAnyRole(*_WRITE_ROLES)()]

    def perform_destroy(self, instance):
        _delete_linked_user(instance)
        instance.delete()


class AccountantViewSet(viewsets.ModelViewSet):
    queryset = Accountant.objects.all()
    serializer_class = AccountantSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [HasAnyRole(*_READ_ROLES)()]
        return [HasAnyRole(*_WRITE_ROLES)()]

    def perform_destroy(self, instance):
        _delete_linked_user(instance)
        instance.delete()


class ManagerViewSet(viewsets.ModelViewSet):
    queryset = Manager.objects.all()
    serializer_class = ManagerSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [HasAnyRole(*_READ_ROLES)()]
        return [HasAnyRole(*_WRITE_ROLES)()]

    def perform_destroy(self, instance):
        _delete_linked_user(instance)
        instance.delete()


class StorekeeperViewSet(viewsets.ModelViewSet):
    queryset = Storekeeper.objects.all()
    serializer_class = StorekeeperSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [HasAnyRole(*_READ_ROLES)()]
        return [HasAnyRole(*_WRITE_ROLES)()]

    def perform_destroy(self, instance):
        _delete_linked_user(instance)
        instance.delete()
