from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from finance.models import EnterpriseBalance, Credit, AccountsPayable
from .serializers import EnterpriseBalanceSerializer, CreditSerializer, AccountsPayableSerializer


def _update_overdue(qs, model):
    today = timezone.now().date()
    model.objects.filter(due_date__lt=today).exclude(status='paid').update(status='overdue')


class EnterpriseBalanceViewSet(viewsets.ModelViewSet):
    queryset = EnterpriseBalance.objects.all()
    serializer_class = EnterpriseBalanceSerializer

    def get_object_or_create(self):
        obj = EnterpriseBalance.objects.first()
        if not obj:
            obj = EnterpriseBalance.objects.create(amount=0)
        return obj

    @action(detail=False, methods=['get'])
    def current(self, request):
        obj = self.get_object_or_create()
        return Response(EnterpriseBalanceSerializer(obj).data)

    @action(detail=False, methods=['patch'])
    def update_balance(self, request):
        obj = self.get_object_or_create()
        amount = request.data.get('amount')
        if amount is None:
            return Response({'error': 'amount обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        obj.amount = amount
        obj.save()
        return Response(EnterpriseBalanceSerializer(obj).data)

    @action(detail=False, methods=['post'])
    def add_funds(self, request):
        obj = self.get_object_or_create()
        delta = request.data.get('delta', 0)
        try:
            obj.amount = float(obj.amount) + float(delta)
            obj.save()
        except (ValueError, TypeError):
            return Response({'error': 'Некорректное значение delta'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EnterpriseBalanceSerializer(obj).data)

    @action(detail=False, methods=['post'])
    def deduct_funds(self, request):
        obj = self.get_object_or_create()
        delta = request.data.get('delta', 0)
        try:
            obj.amount = float(obj.amount) - float(delta)
            obj.save()
        except (ValueError, TypeError):
            return Response({'error': 'Некорректное значение delta'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EnterpriseBalanceSerializer(obj).data)


class CreditViewSet(viewsets.ModelViewSet):
    serializer_class = CreditSerializer

    def get_queryset(self):
        _update_overdue(None, Credit)
        qs = Credit.objects.all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class AccountsPayableViewSet(viewsets.ModelViewSet):
    serializer_class = AccountsPayableSerializer

    def get_queryset(self):
        _update_overdue(None, AccountsPayable)
        qs = AccountsPayable.objects.select_related('id_supplier', 'id_concluded').all()
        status_filter = self.request.query_params.get('status')
        supplier_filter = self.request.query_params.get('supplier')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if supplier_filter:
            qs = qs.filter(id_supplier_id=supplier_filter)
        return qs
