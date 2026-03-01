from rest_framework import serializers
from partners.models import Supplier
from catalog.models import Prices # Импорт из вашего приложения цен

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class SupplierPriceAnalyticSerializer(serializers.Serializer):
    material_name = serializers.CharField(source='id_materials.name')
    current_price = serializers.FloatField(source='price')
    effective_date = serializers.DateField(source='effective_dates')

