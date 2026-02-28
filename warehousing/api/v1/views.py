# pylint: disable=missing-module-docstring,
# pylint: disable=missing-class-docstring,
# pylint: disable=too-few-public-methods

from rest_framework import viewsets, filters
from ...models import Works, Warehouse, Inventory
from .serializers import WarehouseSerializer, WorksSerializer, InventorySerializer

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().distinct()
    serializer_class = WarehouseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'address']

class WorksViewSet(viewsets.ModelViewSet):
    queryset = Works.objects.all()
    serializer_class = WorksSerializer
    
    def get_queryset(self):
        qs = Works.objects.all()
        # Фильтр по складу, если передан ?warehouse_id=1
        warehouse_id = self.request.query_params.get('warehouse_id')
        if warehouse_id:
            qs = qs.filter(id_warehouse=warehouse_id)
        return qs

class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySerializer
    
    def get_queryset(self):
        qs = Inventory.objects.all()
        warehouse_id = self.request.query_params.get('warehouse_id')
        if warehouse_id:
            qs = qs.filter(id_warehouse=warehouse_id)
        return qs.distinct()
