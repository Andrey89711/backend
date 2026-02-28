from rest_framework import serializers
from catalog.models import Materials, Prices

class MaterialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materials
        fields = '__all__'

class PricesSerializer(serializers.ModelSerializer):
    # Дополнительные поля для удобного вывода названий в таблице (режим просмотра)
    material_name = serializers.ReadOnlyField(source='id_materials.name')
    supplier_name = serializers.ReadOnlyField(source='id_supplier.name')

    class Meta:
        model = Prices
        fields = '__all__'
