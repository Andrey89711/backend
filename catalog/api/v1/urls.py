from rest_framework.routers import DefaultRouter
from .views import MaterialsViewSet, PricesViewSet

router = DefaultRouter()
router.register(r'materials', MaterialsViewSet, basename='material')
router.register(r'prices', PricesViewSet, basename='price')

urlpatterns = router.urls
