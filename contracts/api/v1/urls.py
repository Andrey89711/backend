from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConcludedViewSet, ContractViewSet, MaterialsInContractViewSet

router = DefaultRouter()


router.register(r'concluded', ConcludedViewSet, basename='concluded')
router.register(r'materials', MaterialsInContractViewSet, basename='materials-contract')
router.register(r'', ContractViewSet, basename='contract')
urlpatterns = router.urls