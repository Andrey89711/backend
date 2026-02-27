from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, WorksViewSet, InventoryViewSet

router = DefaultRouter()
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'works', WorksViewSet, basename='works')
router.register(r'inventory', InventoryViewSet, basename='inventory')

urlpatterns = router.urls
