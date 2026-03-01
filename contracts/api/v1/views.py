from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count

from ...models import Concluded, Contract, MaterialsInContract
from .serializers import ConcludedSerializer, ContractSerializer, MaterialsInContractSerializer

class ConcludedViewSet(viewsets.ModelViewSet):
    """Заключенные договоры"""
    queryset = Concluded.objects.all().select_related(
        'id_supplier', 
        'id_accountant', 
        'id_manager', 
        'id_director',
        'id_contract'
    ).prefetch_related('id_contract__materialsincontract_set__id_materials')
    
    serializer_class = ConcludedSerializer

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Сводная статистика по договорам"""
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)
        total_count = self.queryset.count()
        total_cost = self.queryset.aggregate(total=Sum('cost'))['total'] or 0

        recent_count = self.queryset.filter(
            conclusion_dates__gte=month_ago
        ).count()

        overdue_payment = self.queryset.filter(
            payment_date__lt=today
        ).count()

        return Response({
            "total_contracts": total_count,
            "total_cost": total_cost,
            "recent_contracts_month": recent_count,
            "overdue_payment_count": overdue_payment
        })

    @action(detail=False, methods=['get'])
    def by_manager(self, request):
        """Группировка договоров по менеджерам"""
        data = self.queryset.values(
            'id_manager__full_name', 
            'id_manager__id'
        ).annotate(
            count=Count('id_contract'),
            total_cost=Sum('cost')
        )
        
        result = [
            {
                "manager_id": item['id_manager__id'],
                "manager_name": item['id_manager__full_name'] or "Не указан",
                "contracts_count": item['count'],
                "total_cost": item['total_cost'] or 0
            }
            for item in data
        ]
        return Response(result)

class ContractViewSet(viewsets.ModelViewSet):
    """База контракта"""
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer

    @action(detail=True, methods=['get'])
    def materials_summary(self, request, pk=None):
        """Краткая сводка по материалам конкретного договора."""
        contract = self.get_object()
        materials_qs = MaterialsInContract.objects.filter(id_contract=contract)
        serializer = MaterialsInContractSerializer(materials_qs, many=True)
        
        total_quantity = sum(m['actual_quantity'] for m in serializer.data)
        
        return Response({
            "contract_id": contract.id_contract,
            "materials_count": materials_qs.count(),
            "total_quantity": total_quantity,
            "details": serializer.data
        })

class MaterialsInContractViewSet(viewsets.ModelViewSet):
    """Материалы в договоре"""
    queryset = MaterialsInContract.objects.all().select_related('id_materials', 'id_contract')
    serializer_class = MaterialsInContractSerializer

    @action(detail=False, methods=['get'])
    def by_contract(self, request):
        """Фильтрация материалов по ID договора."""
        contract_id = request.query_params.get('contract_id')
        if not contract_id:
            return Response({"error": "Параметр contract_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)
        
        qs = self.queryset.filter(id_contract_id=contract_id)
        return Response(self.get_serializer(qs, many=True).data)