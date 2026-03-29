from rest_framework import viewsets
from ...models import Director, Accountant, Manager, Storekeeper
from .serializers import DirectorSerializer, AccountantSerializer, ManagerSerializer, StorekeeperSerializer
from users.permissions import HasAnyRole, ADMIN, DIRECTOR, MANAGER, ACCOUNTANT, STOREKEEPER

_READ_ROLES = (ADMIN, DIRECTOR, MANAGER, ACCOUNTANT, STOREKEEPER)
_WRITE_ROLES = (ADMIN, DIRECTOR, MANAGER) 

class DirectorViewSet(viewsets.ModelViewSet):
    queryset = Director.objects.all()
    serializer_class = DirectorSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [HasAnyRole(*_READ_ROLES)()]
        return [HasAnyRole(*_WRITE_ROLES)()]


class AccountantViewSet(viewsets.ModelViewSet):
    queryset = Accountant.objects.all()
    serializer_class = AccountantSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [HasAnyRole(*_READ_ROLES)()]
        return [HasAnyRole(*_WRITE_ROLES)()]


class ManagerViewSet(viewsets.ModelViewSet):
    queryset = Manager.objects.all()
    serializer_class = ManagerSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [HasAnyRole(*_READ_ROLES)()]
        return [HasAnyRole(*_WRITE_ROLES)()]


class StorekeeperViewSet(viewsets.ModelViewSet):
    queryset = Storekeeper.objects.all()
    serializer_class = StorekeeperSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [HasAnyRole(*_READ_ROLES)()]
        return [HasAnyRole(*_WRITE_ROLES)()]
