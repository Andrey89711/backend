from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .serializers import AdminRegisterSerializer, UserListSerializer
from personnel.models import Director, Accountant, Manager, Storekeeper

User = get_user_model()

ROLE_MODEL_MAP = {
    'directors':    Director,
    'accountants':  Accountant,
    'managers':     Manager,
    'storekeepers': Storekeeper,
}


@api_view(['POST'])
@permission_classes([IsAdminUser])
def register_user(request):
    """POST /api/admin-panel/register/"""
    serializer = AdminRegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'detail': 'Пользователь успешно создан.'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_users(request):
    """GET /api/admin-panel/users/"""
    users = User.objects.all().order_by('-date_joined')
    serializer = UserListSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_personnel(request, role, pk):
    """PATCH /api/admin-panel/personnel/{role}/{pk}/"""
    model = ROLE_MODEL_MAP.get(role)
    if not model:
        return Response({'detail': 'Неизвестная роль.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        instance = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return Response({'detail': 'Запись не найдена.'}, status=status.HTTP_404_NOT_FOUND)

    full_name = request.data.get('full_name')
    contact_information = request.data.get('contact_information')

    if full_name is not None:
        instance.full_name = full_name
    if contact_information is not None:
        instance.contact_information = contact_information

    instance.save()
    return Response({'detail': 'Данные обновлены.'})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def change_personnel_password(request, role, pk):
    model = ROLE_MODEL_MAP.get(role)
    if not model:
        return Response({'detail': 'Неизвестная роль.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        instance = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return Response({'detail': 'Запись не найдена.'}, status=status.HTTP_404_NOT_FOUND)

    password = request.data.get('password')
    if not password:
        return Response({'password': ['Пароль не может быть пустым.']}, status=status.HTTP_400_BAD_REQUEST)

    # Ищем юзера по email = contact_information
    try:
        user = User.objects.get(email=instance.contact_information)
    except User.DoesNotExist:
        return Response(
            {'detail': f'Пользователь с email {instance.contact_information} не найден.'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        validate_password(password, user)
    except ValidationError as e:
        return Response({'password': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.save()
    return Response({'detail': 'Пароль успешно изменён.'})

@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_personnel_user(request, role, pk):
    """GET /api/admin-panel/personnel/{role}/{pk}/user/"""
    model = ROLE_MODEL_MAP.get(role)
    if not model:
        return Response({'detail': 'Неизвестная роль.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        instance = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return Response({'detail': 'Запись не найдена.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        user = User.objects.get(email=instance.contact_information)
        return Response({'username': user.username, 'email': user.email})
    except User.DoesNotExist:
        return Response({'username': None, 'email': instance.contact_information})