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
            return Response(
                {'error': 'Недопустимый статус. Допустимые: ' + ', '.join(allowed)},
                status=status.HTTP_400_BAD_REQUEST
            )
        supplier.status = new_status
        supplier.save()
        return Response({'id_supplier': supplier.id_supplier, 'status': supplier.status})

    @action(detail=True, methods=['get'], url_path='today-prices')
    def today_prices(self, request, pk=None):
        """URL: /api/suppliers/{id}/today-prices/"""
        today = timezone.now().date()

        latest_ids = (
            Prices.objects
            .filter(id_supplier=pk, effective_dates__lte=today)
            .order_by('id_materials', '-effective_dates', '-id_prices')
            .distinct('id_materials')
            .values_list('id_prices', flat=True)
        )

        prices_qs = Prices.objects.filter(id_prices__in=latest_ids).select_related('id_materials')
        serializer = SupplierPriceAnalyticSerializer(prices_qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='compare-prices')
    def compare_prices(self, request, pk=None):
        """URL: /api/suppliers/{id}/compare-prices/"""
        today = timezone.now().date()
        my_prices = self.today_prices(request, pk).data
        comparison = []

        for item in my_prices:
            material_name = item['material_name']
            my_val = item['current_price']

            min_market_price = (
                Prices.objects
                .filter(id_materials__name=material_name, effective_dates__lte=today)
                .exclude(id_supplier=pk)
                .aggregate(Min('price'))['price__min']
            )

            comparison.append({
                "material": material_name,
                "your_price": my_val,
                "market_min": min_market_price,
                "diff_percent": round(
                    ((my_val - min_market_price) / min_market_price * 100), 2
                ) if min_market_price else 0,
            })

        return Response(comparison)

    @action(detail=True, methods=['get'], url_path='price-trend')
    def price_trend(self, request, pk=None):
        """URL: /api/suppliers/{id}/price-trend/"""
        months = int(request.query_params.get('months', 1))
        today = timezone.now().date()
        past_date = today - timedelta(days=30 * months)

        avg_now = (
            Prices.objects
            .filter(
                id_supplier=pk,
                effective_dates__lte=today,
                effective_dates__gt=today - timedelta(days=30),
            )
            .aggregate(Avg('price'))['price__avg'] or 0
        )

        avg_past_query = (
            Prices.objects
            .filter(
                id_supplier=pk,
                effective_dates__lte=past_date,
                effective_dates__gt=past_date - timedelta(days=30),
            )
            .aggregate(Avg('price'))['price__avg']
        )

        if not avg_past_query:
            first_record = Prices.objects.filter(id_supplier=pk).order_by('effective_dates').first()
            avg_past = first_record.price if first_record else 0
        else:
            avg_past = avg_past_query

        if avg_past == 0:
            return Response({"message": "У поставщика нет истории цен"}, status=200)

        if avg_now == 0:
            last_record = Prices.objects.filter(id_supplier=pk).order_by('-effective_dates').first()
            avg_now = last_record.price if last_record else 0

        trend_percent = ((avg_now - avg_past) / avg_past) * 100

        return Response({
            "period_months": months,
            "average_start_price": round(avg_past, 2),
            "average_current_price": round(avg_now, 2),
            "trend_percent": f"{round(trend_percent, 2)}%",
            "label": "Подорожало" if trend_percent > 0 else "Подешевело",
        })

    @action(detail=False, methods=['get'], url_path='all-trends')
    def all_trends(self, request):
        """
        URL: /api/suppliers/all-trends/
        Возвращает тренд цен для каждого поставщика за последний месяц.
        """
        months = int(request.query_params.get('months', 1))
        today = timezone.now().date()
        past_date = today - timedelta(days=30 * months)

        suppliers = Supplier.objects.all()
        result = []

        for supplier in suppliers:
            pk = supplier.id_supplier

            avg_now = (
                Prices.objects
                .filter(
                    id_supplier=pk,
                    effective_dates__lte=today,
                    effective_dates__gt=today - timedelta(days=30),
                )
                .aggregate(Avg('price'))['price__avg']
            )

            avg_past_query = (
                Prices.objects
                .filter(
                    id_supplier=pk,
                    effective_dates__lte=past_date,
                    effective_dates__gt=past_date - timedelta(days=30),
                )
                .aggregate(Avg('price'))['price__avg']
            )

            if not avg_past_query:
                first_record = (
                    Prices.objects.filter(id_supplier=pk).order_by('effective_dates').first()
                )
                avg_past = float(first_record.price) if first_record else None
            else:
                avg_past = float(avg_past_query)

            if avg_now is None:
                last_record = (
                    Prices.objects.filter(id_supplier=pk).order_by('-effective_dates').first()
                )
                avg_now = float(last_record.price) if last_record else None

            if avg_past is None or avg_now is None or avg_past == 0:
                continue

            trend_percent = ((avg_now - avg_past) / avg_past) * 100

            result.append({
                "supplier_id": pk,
                "supplier_name": supplier.name,
                "period_months": months,
                "average_start_price": round(avg_past, 2),
                "average_current_price": round(avg_now, 2),
                "trend_percent": f"{round(trend_percent, 2)}%",
                "label": "Подорожало" if trend_percent > 0 else "Подешевело",
            })

        return Response(result)

    @action(detail=False, methods=['get'], url_path='all-compare')
    def all_compare(self, request):
        """
        URL: /api/suppliers/all-compare/
        Для каждого поставщика и каждого его материала сравнивает цену
        с минимальной рыночной ценой остальных поставщиков.
        """
        today = timezone.now().date()
        suppliers = Supplier.objects.all()
        result = []

        for supplier in suppliers:
            pk = supplier.id_supplier

            latest_ids = (
                Prices.objects
                .filter(id_supplier=pk, effective_dates__lte=today)
                .order_by('id_materials', '-effective_dates', '-id_prices')
                .distinct('id_materials')
                .values_list('id_prices', flat=True)
            )

            prices_qs = (
                Prices.objects
                .filter(id_prices__in=latest_ids)
                .select_related('id_materials')
            )

            for price_obj in prices_qs:
                material_name = price_obj.id_materials.name
                my_val = float(price_obj.price)

                min_market_price = (
                    Prices.objects
                    .filter(id_materials__name=material_name, effective_dates__lte=today)
                    .exclude(id_supplier=pk)
                    .aggregate(Min('price'))['price__min']
                )

                if min_market_price is None:
                    diff_percent = 0
                else:
                    min_market_price = float(min_market_price)
                    diff_percent = round(
                        ((my_val - min_market_price) / min_market_price * 100), 2
                    ) if min_market_price else 0

                result.append({
                    "supplier_id": pk,
                    "supplier_name": supplier.name,
                    "material": material_name,
                    "your_price": my_val,
                    "market_min": min_market_price,
                    "diff_percent": diff_percent,
                })

        return Response(result)