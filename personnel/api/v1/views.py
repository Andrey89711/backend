from rest_framework import viewsets
from ...models import Director, Accountant, Manager, Storekeeper
from .serializers import DirectorSerializer, AccountantSerializer, ManagerSerializer, StorekeeperSerializer

class DirectorViewSet(viewsets.ModelViewSet):
    queryset = Director.objects.all()
    serializer_class = DirectorSerializer

class AccountantViewSet(viewsets.ModelViewSet):
    queryset = Accountant.objects.all()
    serializer_class = AccountantSerializer

class ManagerViewSet(viewsets.ModelViewSet):
    queryset = Manager.objects.all()
    serializer_class = ManagerSerializer

class StorekeeperViewSet(viewsets.ModelViewSet):
    queryset = Storekeeper.objects.all()
    serializer_class = StorekeeperSerializer