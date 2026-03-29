from rest_framework import viewsets, filters
from ...models import Works, Warehouse, Inventory
from .serializers import WarehouseSerializer, WorksSerializer, InventorySerializer
from users.permissions import HasAnyRole, ADMIN, STOREKEEPER, MANAGER, DIRECTOR

_WAREHOUSE_ROLES = (ADMIN, STOREKEEPER, MANAGER, DIRECTOR)


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().distinct()
    serializer_class = WarehouseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'address']

    def get_permissions(self):
        return [HasAnyRole(*_WAREHOUSE_ROLES)()]


class WorksViewSet(viewsets.ModelViewSet):
    queryset = Works.objects.all()
    serializer_class = WorksSerializer

    def get_permissions(self):
        return [HasAnyRole(*_WAREHOUSE_ROLES)()]

    def get_queryset(self):
        qs = Works.objects.all()
        warehouse_id = self.request.query_params.get('warehouse_id')
        if warehouse_id:
            qs = qs.filter(id_warehouse=warehouse_id)
        return qs


class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySerializer

    def get_permissions(self):
        return [HasAnyRole(*_WAREHOUSE_ROLES)()]

    def get_queryset(self):
        qs = Inventory.objects.all()
        warehouse_id = self.request.query_params.get('warehouse_id')
        if warehouse_id:
            qs = qs.filter(id_warehouse=warehouse_id)
        return qs.distinct()
