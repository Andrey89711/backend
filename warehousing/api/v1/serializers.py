# pylint: disable=missing-module-docstring,
# pylint: disable=missing-class-docstring,
# pylint: disable=too-few-public-methods

from rest_framework import serializers
from ...models import Inventory, Works, Warehouse

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id_warehouse', 'name', 'address']
        read_only_fields = ['id_warehouse']

class WorksSerializer(serializers.ModelSerializer):
    storekeeper_name = serializers.ReadOnlyField(source='id_storekeeper.full_name')
    warehouse_name = serializers.ReadOnlyField(source='id_warehouse.name')

    class Meta:
        model = Works
        fields = ['id', 'id_storekeeper', 'storekeeper_name', 'id_warehouse', 'warehouse_name']

class InventorySerializer(serializers.ModelSerializer):
    warehouse_name = serializers.ReadOnlyField(source='id_warehouse.name')
    material_name = serializers.ReadOnlyField(source='id_materials.name')

    class Meta:
        model = Inventory
        fields = ['id', 'quantity', 'id_warehouse', 'warehouse_name', 'id_materials', 'material_name']
