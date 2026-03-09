from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    LogoutSerializer
)
from drf_spectacular.utils import extend_schema
from users.models import EmailVerificationToken


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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.is_active = False
        user.save()

        token_obj = EmailVerificationToken.objects.create(user=user)
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token_obj.token}"
        send_mail(
            subject='Подтвердите ваш email',
            message=f'Для подтверждения email перейдите по ссылке:\n{verify_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
        return Response(
            {'message': 'Регистрация успешна. Проверьте email для подтверждения.'},
            status=status.HTTP_201_CREATED
        )


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
        
        # Сначала ищем пользователя вручную, чтобы различить 401 и 403
        try:
            candidate = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'Неверные учетные данные'}, status=status.HTTP_401_UNAUTHORIZED)

        if not candidate.check_password(password):
            return Response({'error': 'Неверные учетные данные'}, status=status.HTTP_401_UNAUTHORIZED)

        if not candidate.is_active:
            return Response(
                {'error': 'Email не подтверждён. Проверьте вашу почту.'},
                status=status.HTTP_403_FORBIDDEN
            )

        user = candidate
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


class TokenRefreshView(BaseTokenRefreshView):
    """Обновление access токена"""
    permission_classes = [permissions.AllowAny]
    
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


class VerifyEmailView(generics.GenericAPIView):
    """Подтверждение email по токену"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Токен не передан'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token_obj = EmailVerificationToken.objects.select_related('user').get(token=token)
        except (EmailVerificationToken.DoesNotExist, Exception):
            return Response({'error': 'Неверный или просроченный токен'}, status=status.HTTP_400_BAD_REQUEST)

        user = token_obj.user
        user.is_active = True
        user.save()
        token_obj.delete()
        return Response({'message': 'Email успешно подтверждён. Теперь вы можете войти.'})


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