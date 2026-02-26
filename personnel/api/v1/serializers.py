from rest_framework import serializers
from ...models import Director, Accountant, Manager, Storekeeper

class DirectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Director
        fields = ['id_director', 'full_name', 'contact_information']
        read_only_fields = ['id_director']

class AccountantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accountant
        fields = ['id_accountant', 'full_name', 'contact_information']
        read_only_fields = ['id_accountant']

class ManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manager
        fields = ['id_manager', 'full_name', 'contact_information']
        read_only_fields = ['id_manager']

class StorekeeperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Storekeeper
        fields = ['id_storekeeper', 'full_name', 'contact_information']
        read_only_fields = ['id_storekeeper']