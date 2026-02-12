from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .serializers import (
    RegisterSerializer, 
    LoginSerializer, 
    UserSerializer,
    LogoutSerializer
)
from drf_spectacular.utils import extend_schema


class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя"""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary="Регистрация пользователя",
        description="Создает нового пользователя и возвращает JWT токены",
        responses={201: RegisterSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LoginView(generics.GenericAPIView):
    """Вход в систему"""
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary="Вход в систему",
        description="Аутентификация пользователя и получение JWT токенов",
        responses={200: LoginSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response(
                {'error': 'Неверные учетные данные'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


class TokenRefreshView(BaseTokenRefreshView):
    """Обновление access токена"""
    
    @extend_schema(
        summary="Обновление токена",
        description="Получение нового access токена по refresh токену",
        responses={200: {'type': 'object', 'properties': {'access': {'type': 'string'}}}}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(generics.GenericAPIView):
    """Выход из системы"""
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Выход из системы",
        description="Добавление refresh токена в черный список",
        responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            refresh_token = serializer.validated_data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({'message': 'Выход выполнен успешно'})
        except TokenError:
            return Response(
                {'error': 'Неверный или просроченный токен'},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserDetailView(generics.RetrieveAPIView):
    """Информация о текущем пользователе"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Данные текущего пользователя",
        description="Возвращает информацию о текущем авторизованном пользователе"
    )
    def get_object(self):
        return self.request.user