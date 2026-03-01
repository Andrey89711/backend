from rest_framework.routers import DefaultRouter
from .views import SupplierViewSet

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')

urlpatterns = router.urls

# Действие,Метод,URL
# Список всех поставщиков,GET,/api/partners/
# Актуальные цены (Сегодня),GET,/api/partners/suppliers/3/today-prices/
# Сравнение с рынком,GET,/api/partners/suppliers/{id}/compare-prices/
# Тенденция (аналитика),GET,/api/partners/suppliers/{id}/price-trend/
