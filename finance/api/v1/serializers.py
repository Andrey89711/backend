from rest_framework import serializers
from finance.models import EnterpriseBalance, Credit, AccountsPayable


class EnterpriseBalanceSerializer(serializers.ModelSerializer):
    director_name = serializers.ReadOnlyField(source='id_director.full_name')

    class Meta:
        model = EnterpriseBalance
        fields = ['id', 'amount', 'updated_at', 'id_director', 'director_name']
        read_only_fields = ['updated_at']


class CreditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credit
        fields = '__all__'


class AccountsPayableSerializer(serializers.ModelSerializer):
    supplier_name = serializers.ReadOnlyField(source='id_supplier.name')

    class Meta:
        model = AccountsPayable
        fields = '__all__'
