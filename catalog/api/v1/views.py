from rest_framework import viewsets, filters
from catalog.models import Materials, Prices
from .serializers import MaterialsSerializer, PricesSerializer
from django.utils import timezone
from django.db.models import OuterRef, Subquery
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime
from django.db.models import Min, Q

class MaterialsViewSet(viewsets.ModelViewSet):
    queryset = Materials.objects.all()
    serializer_class = MaterialsSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

class PricesViewSet(viewsets.ModelViewSet):
    queryset = Prices.objects.all()
    serializer_class = PricesSerializer

    def get_target_date(self, request):
        """Парсим дату из параметров ?date=YYYY-MM-DD
        GET /api/catalog/prices/filtered_by_date/?date=2026-02-28
            Если параметр не указан, используем текущую дату.
        """
        date_param = request.query_params.get('date')
        if date_param:
            try:
                return datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return None
        return timezone.now().date()

    # 1. Эндпоинт: .../prices/filtered_by_date/
    @action(detail=False, methods=['get'])
    def filtered_by_date(self, request):
        target_date = self.get_target_date(request)
        if not target_date:
            return Response({"error": "Неверный формат даты"}, status=400)

        # Выбираем последние записи цен для каждого сочетания Материал+Поставщик
        latest_ids = Prices.objects.filter(
            id_materials=OuterRef('id_materials'),
            id_supplier=OuterRef('id_supplier'),
            effective_dates__lte=target_date
        ).order_by('-effective_dates', '-id_prices').values('id_prices')[:1]

        queryset = Prices.objects.filter(id_prices__in=Subquery(latest_ids))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # 2. Эндпоинт: .../prices/best_offers/
    @action(detail=False, methods=['get'])
    def best_offers(self, request):
        """"
        Возвращает лучшие предложения (минимальные цены) по каждому материалу на дату.
        Параметры: ?date=YYYY-MM-DD
        GET /api/catalog/prices/best_offers/?date=2026-02-28
        """
        target_date = self.get_target_date(request)
        if not target_date:
            return Response({"error": "Неверный формат даты"}, status=400)

        # Сначала получаем актуальный срез (как в методе выше)
        actual_ids = Prices.objects.filter(
            id_materials=OuterRef('id_materials'),
            id_supplier=OuterRef('id_supplier'),
            effective_dates__lte=target_date
        ).order_by('-effective_dates', '-id_prices').values('id_prices')[:1]
        
        actual_prices = Prices.objects.filter(id_prices__in=Subquery(actual_ids))

        # Находим минимальные цены среди этого среза
        min_prices_map = actual_prices.values('id_materials').annotate(min_val=Min('price'))
        
        # Фильтруем, чтобы оставить только лучшие предложения
        q_filter = Q()
        for item in min_prices_map:
            q_filter |= Q(id_materials=item['id_materials'], price=item['min_val'])
        
        if not min_prices_map.exists():
            return Response([])

        final_queryset = actual_prices.filter(q_filter)
        serializer = self.get_serializer(final_queryset, many=True)
        return Response(serializer.data)

    # 3. Эндпоинт: .../prices/filtered_by_partners/
    @action(detail=False, methods=['get'])
    def filtered_by_partners(self, request):
        """
        Возвращает актуальные цены конкретного поставщика на дату.
        Параметры: ?supplier_id=1&date=2026-02-28
        GET /api/catalog/prices/filtered_by_partners/?supplier_id=5&date=2026-02-28
        """
        target_date = self.get_target_date(request)
        supplier_id = request.query_params.get('supplier_id')

        if not target_date:
            return Response({"error": "Неверный формат даты. Используйте YYYY-MM-DD"}, status=400)
        
        if not supplier_id:
            return Response({"error": "Необходимо указать supplier_id в параметрах запроса"}, status=400)

        # Выбираем последние записи цен для каждого материала, 
        # но только для указанного поставщика
        latest_ids = Prices.objects.filter(
            id_materials=OuterRef('id_materials'),
            id_supplier=supplier_id,
            effective_dates__lte=target_date
        ).order_by('-effective_dates', '-id_prices').values('id_prices')[:1]

        queryset = Prices.objects.filter(id_prices__in=Subquery(latest_ids))
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
