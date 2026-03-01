from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeliveryViewSet, ActOfArrivalViewSet, AcceptanceOfDeliveryViewSet

router = DefaultRouter()
router.register(r'deliveries', DeliveryViewSet, basename='delivery')
router.register(r'acts-of-arrival', ActOfArrivalViewSet, basename='act-arrival')
router.register(r'acceptances', AcceptanceOfDeliveryViewSet, basename='acceptance')

urlpatterns = [
    path('', include(router.urls)),
]
