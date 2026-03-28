from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from personnel.models import Director, Accountant, Manager, Storekeeper

User = get_user_model()

ROLE_CHOICES = (
    ('directors',    'Директор'),
    ('accountants',  'Бухгалтер'),
    ('managers',     'Менеджер'),
    ('storekeepers', 'Кладовщик'),
)

ROLE_MODEL_MAP = {
    'directors':    Director,
    'accountants':  Accountant,
    'managers':     Manager,
    'storekeepers': Storekeeper,
}


class AdminRegisterSerializer(serializers.Serializer):
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
        )

        model = ROLE_MODEL_MAP[role]
        model.objects.create(
            full_name=full_name,
            contact_information=contact_information,
        )

        return user


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = [
            'id', 'username', 'email',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined',
        ]