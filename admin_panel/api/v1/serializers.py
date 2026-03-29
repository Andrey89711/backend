from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from admin_panel.models import Admin
from personnel.models import Director, Accountant, Manager, Storekeeper
from users.models import UserProfile

User = get_user_model()

ROLE_CHOICES = (
    ('directors',    'Директор'),
    ('accountants',  'Бухгалтер'),
    ('managers',     'Менеджер'),
    ('storekeepers', 'Кладовщик'),
)

ROLE_MODEL_MAP = {
    'directors':    (Director,    'director'),
    'accountants':  (Accountant,  'accountant'),
    'managers':     (Manager,     'manager'),
    'storekeepers': (Storekeeper, 'storekeeper'),
}


class AdminRegisterSerializer(serializers.Serializer):
    """Регистрация сотрудника (director/accountant/manager/storekeeper) администратором."""
    username            = serializers.CharField(max_length=150)
    email               = serializers.EmailField()
    password            = serializers.CharField(write_only=True)
    password2           = serializers.CharField(write_only=True)
    role                = serializers.ChoiceField(choices=ROLE_CHOICES)
    full_name           = serializers.CharField(max_length=200)
    contact_information = serializers.CharField(max_length=300)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Пользователь с таким именем уже существует.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует.')
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Пароли не совпадают.'})
        validate_password(data['password'])
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        role                = validated_data.pop('role')
        full_name           = validated_data.pop('full_name')
        contact_information = validated_data.pop('contact_information')

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=True,
        )

        model, profile_role = ROLE_MODEL_MAP[role]
        model.objects.create(full_name=full_name, contact_information=contact_information)
        UserProfile.objects.update_or_create(user=user, defaults={'role': profile_role})

        return user


class UserListSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        if obj.is_superuser:
            return 'superadmin'
        profile = getattr(obj, 'profile', None)
        return profile.role if profile else 'viewer'

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'role']


class AdminSerializer(serializers.ModelSerializer):
    """Сериализатор записи Admin (таблица admin)."""
    class Meta:
        model  = Admin
        fields = ['id_admin', 'full_name', 'contact_information']


class CreateAdminSerializer(serializers.Serializer):
    """Создание пользователя с ролью admin (только для superadmin)."""
    username            = serializers.CharField(max_length=150)
    email               = serializers.EmailField()
    password            = serializers.CharField(write_only=True)
    password2           = serializers.CharField(write_only=True)
    full_name           = serializers.CharField(max_length=200)
    contact_information = serializers.CharField(max_length=300)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Пользователь с таким именем уже существует.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует.')
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Пароли не совпадают.'})
        validate_password(data['password'])
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        full_name           = validated_data.pop('full_name')
        contact_information = validated_data.pop('contact_information')

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=True,
            is_staff=True,
        )
        UserProfile.objects.update_or_create(user=user, defaults={'role': 'admin'})
        Admin.objects.create(full_name=full_name, contact_information=contact_information)

        return user
