from rest_framework import serializers
from partners.models import Supplier

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'  # Включает все поля, включая id_supplier
