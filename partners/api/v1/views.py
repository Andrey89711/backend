from rest_framework import viewsets, filters
from partners.models import Supplier
from .serializers import SupplierSerializer

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filter_backends = [filters.SearchFilter]
    # Позволяем искать по названию компании и ИНН
    search_fields = ['name', 'tax_id']
