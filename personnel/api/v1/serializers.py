from django.contrib.auth import get_user_model
from rest_framework import serializers
from ...models import Director, Accountant, Manager, Storekeeper

User = get_user_model()


def get_username_by_email(email: str) -> str | None:
    try:
        return User.objects.get(email=email).username
    except User.DoesNotExist:
        return None


class DirectorSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Director
        fields = ['id_director', 'full_name', 'contact_information', 'username']
        read_only_fields = ['id_director', 'username']

    def get_username(self, obj):
        return get_username_by_email(obj.contact_information)


class AccountantSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Accountant
        fields = ['id_accountant', 'full_name', 'contact_information', 'username']
        read_only_fields = ['id_accountant', 'username']

    def get_username(self, obj):
        return get_username_by_email(obj.contact_information)


class ManagerSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Manager
        fields = ['id_manager', 'full_name', 'contact_information', 'username']
        read_only_fields = ['id_manager', 'username']

    def get_username(self, obj):
        return get_username_by_email(obj.contact_information)


class StorekeeperSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Storekeeper
        fields = ['id_storekeeper', 'full_name', 'contact_information', 'username']
        read_only_fields = ['id_storekeeper', 'username']

    def get_username(self, obj):
        return get_username_by_email(obj.contact_information)