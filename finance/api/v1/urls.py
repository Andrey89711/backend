from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EnterpriseBalanceViewSet, CreditViewSet, AccountsPayableViewSet

router = DefaultRouter()
router.register(r'balance', EnterpriseBalanceViewSet, basename='balance')
router.register(r'credits', CreditViewSet, basename='credit')
router.register(r'payables', AccountsPayableViewSet, basename='payable')

urlpatterns = [
    path('', include(router.urls)),
]
