from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/auth/', include('users.api.v1.urls')),
    path('api/personnel/', include('personnel.api.v1.urls')),
    path('api/partners/', include('partners.api.v1.urls')),
    path('api/catalog/', include('catalog.api.v1.urls')),
    path('api/warehousing/', include('warehousing.api.v1.urls')),
    path('api/contracts/', include('contracts.api.v1.urls')),
    path('api/deliveries/', include('deliveries.api.v1.urls')),
    
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
