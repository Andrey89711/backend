from rest_framework.routers import DefaultRouter
from .views import DirectorViewSet, AccountantViewSet, ManagerViewSet, StorekeeperViewSet

router = DefaultRouter()
router.register(r'directors', DirectorViewSet, basename='director')
router.register(r'accountants', AccountantViewSet, basename='accountant')
router.register(r'managers', ManagerViewSet, basename='manager')
router.register(r'storekeepers', StorekeeperViewSet, basename='storekeeper')

urlpatterns = router.urls