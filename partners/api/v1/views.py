from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Avg, Min, OuterRef, Subquery
from datetime import timedelta

from partners.models import Supplier
from catalog.models import Prices
from .serializers import SupplierSerializer, SupplierPriceAnalyticSerializer

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'tax_id']

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        """Смена статуса поставщика: pending / approved / active"""
        supplier = self.get_object()
        new_status = request.data.get('status')
        allowed = ['pending', 'approved', 'active']
        if new_status not in allowed:
            return Response({'error': 'Недопустимый статус. Допустимые: ' + ', '.join(allowed)}, status=status.HTTP_400_BAD_REQUEST)
        supplier.status = new_status
        supplier.save()
        return Response({'id_supplier': supplier.id_supplier, 'status': supplier.status})

    # 1. Актуальные цены поставщика на сегодня
    @action(detail=True, methods=['get'], url_path='today-prices')
    def today_prices(self, request, pk=None):
        """URL: /api/suppliers/{id}/today-prices/"""
        today = timezone.now().date()
        

        latest_ids = Prices.objects.filter(
            id_supplier=pk,
            effective_dates__lte=today
        ).order_by('id_materials', '-effective_dates', '-id_prices').distinct('id_materials').values_list('id_prices', flat=True)

        prices_qs = Prices.objects.filter(id_prices__in=latest_ids).select_related('id_materials')
        serializer = SupplierPriceAnalyticSerializer(prices_qs, many=True)
        return Response(serializer.data)

    # 2. Сравнение с конкурентами по материалам поставщика
    @action(detail=True, methods=['get'], url_path='compare-prices')
    def compare_prices(self, request, pk=None):
        """URL: /api/suppliers/{id}/compare-prices/"""
        today = timezone.now().date()
        

        my_prices = self.today_prices(request, pk).data
        comparison = []

        for item in my_prices:
            material_name = item['material_name']
            my_val = item['current_price']
            
            # Ищем минимальную цену на этот же материал среди ВСЕХ остальных
            min_market_price = Prices.objects.filter(
                id_materials__name=material_name,
                effective_dates__lte=today
            ).exclude(id_supplier=pk).aggregate(Min('price'))['price__min']

            comparison.append({
                "material": material_name,
                "your_price": my_val,
                "market_min": min_market_price,
                "diff_percent": round(((my_val - min_market_price) / min_market_price * 100), 2) if min_market_price else 0
            })
        
        return Response(comparison)

    @action(detail=True, methods=['get'], url_path='price-trend')
    def price_trend(self, request, pk=None):
        months = int(request.query_params.get('months', 1))
        today = timezone.now().date()
        past_date = today - timedelta(days=30 * months)


        avg_now = Prices.objects.filter(
            id_supplier=pk, 
            effective_dates__lte=today,
            effective_dates__gt=today - timedelta(days=30)
        ).aggregate(Avg('price'))['price__avg'] or 0


        avg_past_query = Prices.objects.filter(
            id_supplier=pk,
            effective_dates__lte=past_date,
            effective_dates__gt=past_date - timedelta(days=30)
        ).aggregate(Avg('price'))['price__avg']


        if not avg_past_query:
            first_price_record = Prices.objects.filter(id_supplier=pk).order_by('effective_dates').first()
            avg_past = first_price_record.price if first_price_record else 0
        else:
            avg_past = avg_past_query


        if avg_past == 0:
            return Response({"message": "У поставщика нет истории цен"}, status=200)


        if avg_now == 0:
            last_price_record = Prices.objects.filter(id_supplier=pk).order_by('-effective_dates').first()
            avg_now = last_price_record.price if last_price_record else 0

        trend_percent = ((avg_now - avg_past) / avg_past) * 100

        return Response({
            "period_months": months,
            "average_start_price": round(avg_past, 2), # Цена с которой сравниваем
            "average_current_price": round(avg_now, 2), # Последняя цена
            "trend_percent": f"{round(trend_percent, 2)}%",
            "label": "Подорожало" if trend_percent > 0 else "Подешевело"
        })
