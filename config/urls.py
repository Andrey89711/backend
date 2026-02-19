from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # JWT Auth endpoints
    path('api/auth/', include('users.urls')),
    path('api/personnel/', include('personnel.urls')),
    path('api/partners/', include('partners.urls')),
    path('api/catalog/', include('catalog.urls')),
    path('api/warehousing/', include('warehousing.urls')),
    path('api/contracts/', include('contracts.urls')),
    path('api/deliveries/', include('deliveries.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
