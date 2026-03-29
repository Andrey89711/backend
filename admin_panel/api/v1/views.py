from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from admin_panel.models import Admin
from users.models import UserProfile
from users.permissions import HasAnyRole, IsSuperAdmin, ADMIN
from .serializers import (
    AdminRegisterSerializer,
    AdminSerializer,
    CreateAdminSerializer,
    UserListSerializer,
)
from personnel.models import Director, Accountant, Manager, Storekeeper

User = get_user_model()

ROLE_MODEL_MAP = {
    'directors':    Director,
    'accountants':  Accountant,
    'managers':     Manager,
    'storekeepers': Storekeeper,
}

_IsAdminOrSuper = HasAnyRole(ADMIN)


@api_view(['POST'])
@permission_classes([_IsAdminOrSuper])
def register_user(request):
    """POST /api/admin-panel/register/ — создать сотрудника (admin + superadmin)"""
    serializer = AdminRegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'detail': 'Пользователь успешно создан.'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([_IsAdminOrSuper])
def list_users(request):
    """GET /api/admin-panel/users/"""
    users = User.objects.all().order_by('-date_joined')
    serializer = UserListSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([_IsAdminOrSuper])
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
@permission_classes([_IsAdminOrSuper])
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
@permission_classes([_IsAdminOrSuper])
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


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def list_admins(request):
    """GET /api/admin-panel/admins/ — список всех администраторов"""
    admins = Admin.objects.all()
    return Response(AdminSerializer(admins, many=True).data)


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def create_admin(request):
    """POST /api/admin-panel/admins/ — создать нового администратора"""
    serializer = CreateAdminSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'detail': 'Администратор успешно создан.'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsSuperAdmin])
def delete_admin(request, pk):
    """DELETE /api/admin-panel/admins/{pk}/ — удалить администратора"""
    try:
        admin_record = Admin.objects.get(pk=pk)
    except Admin.DoesNotExist:
        return Response({'detail': 'Администратор не найден.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        user = User.objects.get(email=admin_record.contact_information)
        profile = getattr(user, 'profile', None)
        if profile:
            profile.role = 'viewer'
            profile.save(update_fields=['role'])
        user.is_staff = False
        user.save(update_fields=['is_staff'])
    except User.DoesNotExist:
        pass

    admin_record.delete()
    return Response({'detail': 'Администратор удалён.'}, status=status.HTTP_200_OK)
