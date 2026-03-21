from rest_framework import viewsets, filters
from catalog.models import Materials, Prices
from .serializers import MaterialsSerializer, PricesSerializer
from django.utils import timezone
from django.db.models import Sum, Q
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime
from ...models import Materials, Prices
from contracts.models import MaterialsInContract, Concluded

class MaterialsViewSet(viewsets.ModelViewSet):
    queryset = Materials.objects.all()
    serializer_class = MaterialsSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Возвращает статистику по материалам: суммарное количество по всем договорам.
        Формат: {"Название материала": суммарное_количество, ...}
        """
        # Агрегируем сумму materials_quality_in_contract для каждого материала
        concluded_contract_ids = Concluded.objects.values_list('id_contract', flat=True)
        
        data = (
            MaterialsInContract.objects
            .filter(id_contract_id__in=concluded_contract_ids)
            .values('id_materials__name')
            .annotate(total_quantity=Sum('materials_quality_in_contract'))
            .order_by('-total_quantity')
        )
        result = {item['id_materials__name']: item['total_quantity'] or 0 for item in data}
        return Response(result)


    @action(detail=False, methods=['get'])
    def analysis(self, request):
        """
        Возвращает материалы с заданным min/max количеством и фактическим остатком.
        Статусы: ok / low / high / critical
        """
        from warehousing.models import Inventory
        qs = Materials.objects.filter(
            Q(min_quantity__isnull=False) | Q(max_quantity__isnull=False)
        )
        result = []
        for mat in qs:
            total = Inventory.objects.filter(id_materials=mat).aggregate(
                total=Sum('quantity')
            )['total'] or 0

            mn = mat.min_quantity
            mx = mat.max_quantity

            if total == 0 and mn is not None and mn > 0:
                s = 'critical'
            elif mn is not None and total < mn:
                s = 'low'
            elif mx is not None and total > mx:
                s = 'high'
            else:
                s = 'ok'

            result.append({
                'id': mat.id_materials,
                'name': mat.name,
                'unit_of_measurement': mat.unit_of_measurement,
                'min_quantity': mn,
                'max_quantity': mx,
                'total_quantity': total,
                'status': s,
            })
        return Response(result)

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
        # Используем list() и .first() для совместимости с MySQL без LIMIT в subquery
        query = Prices.objects.values('id_materials', 'id_supplier').filter(
            effective_dates__lte=target_date
        ).distinct()
        
        latest_ids = []
        for material_supplier in query:
            latest = Prices.objects.filter(
                id_materials=material_supplier['id_materials'],
                id_supplier=material_supplier['id_supplier'],
                effective_dates__lte=target_date
            ).order_by('-effective_dates', '-id_prices').values_list('id_prices', flat=True).first()
            if latest:
                latest_ids.append(latest)

        queryset = Prices.objects.filter(id_prices__in=latest_ids)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # 2. Эндпоинт: .../prices/best_offers/
    @action(detail=False, methods=['get'])
    def best_offers(self, request):
        """
        Возвращает лучшие предложения (минимальные цены) по каждому материалу на дату.
        Параметры: ?date=YYYY-MM-DD
        GET /api/catalog/prices/best_offers/?date=2026-02-28
        """
        target_date = self.get_target_date(request)
        if not target_date:
            return Response({"error": "Неверный формат даты"}, status=400)

        # Получаем актуальный срез: последняя цена на каждое сочетание материал+поставщик
        # Используем queryset.values_list() и list() для совместимости с MySQL без LIMIT в subquery
        query = Prices.objects.values('id_materials', 'id_supplier').filter(
            effective_dates__lte=target_date
        ).distinct()
        
        actual_prices = []
        for material_supplier in query:
            latest = Prices.objects.filter(
                id_materials=material_supplier['id_materials'],
                id_supplier=material_supplier['id_supplier'],
                effective_dates__lte=target_date
            ).order_by('-effective_dates', '-id_prices').first()
            if latest:
                actual_prices.append(latest)

        if not actual_prices:
            return Response([])

        # Находим минимальную цену по каждому материалу (в Python, чтобы избежать
        # сложных вложенных запросов)
        best_by_material: dict = {}
        for p in actual_prices:
            mat_id = p.id_materials_id
            if mat_id not in best_by_material or p.price < best_by_material[mat_id].price:
                best_by_material[mat_id] = p

        serializer = self.get_serializer(list(best_by_material.values()), many=True)
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
        materials_query = Prices.objects.values('id_materials').filter(
            id_supplier=supplier_id,
            effective_dates__lte=target_date
        ).distinct()
        
        latest_ids = []
        for material in materials_query:
            latest = Prices.objects.filter(
                id_materials=material['id_materials'],
                id_supplier=supplier_id,
                effective_dates__lte=target_date
            ).order_by('-effective_dates', '-id_prices').values_list('id_prices', flat=True).first()
            if latest:
                latest_ids.append(latest)

        queryset = Prices.objects.filter(id_prices__in=latest_ids)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
