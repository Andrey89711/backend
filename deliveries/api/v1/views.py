import logging
from datetime import datetime, timedelta
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from contracts.models import Contract, MaterialsInContract
from contracts.services.documents import generate_arrival_pdf, generate_divergence_pdf
from deliveries.choices import DeliveryStatus
from deliveries.models import AcceptanceOfDelivery, ActOfArrival, Delivery
from warehousing.models import Inventory, Works
from users.permissions import HasAnyRole, ADMIN, STOREKEEPER, MANAGER, DIRECTOR, ACCOUNTANT

_DELIVERY_ROLES = (ADMIN, STOREKEEPER, MANAGER, DIRECTOR, ACCOUNTANT)
from .serializers import (
    DeliverySerializer,
    ActOfArrivalSerializer,
    AcceptanceOfDeliverySerializer,
    StartReceivingRequestSerializer,
    ConfirmAcceptanceRequestSerializer,
)

logger = logging.getLogger(__name__)


def _auto_delay(qs):
    """Помечает просроченные доставки как DELAYED."""
    today = timezone.now().date()
    not_terminal = [DeliveryStatus.IN_TRANSIT, DeliveryStatus.PENDING, DeliveryStatus.NOT_DELIVERED]
    qs.filter(delivery_date__lt=today, status__in=not_terminal).update(status=DeliveryStatus.DELAYED)


def _is_good_condition(condition: str | None) -> bool:
    if not condition:
        return True
    normalized = condition.strip().lower()
    bad_markers = ('брак', 'плох', 'поврежден', 'неудовл', 'bad', 'damag')
    return not any(marker in normalized for marker in bad_markers)


def _build_divergence_items(materials_qs):
    items = []
    for mic in materials_qs.select_related('id_materials'):
        planned = mic.materials_quality_in_contract or 0
        actual = mic.actual_quantity if mic.actual_quantity is not None else planned
        has_qty_diff = float(planned) != float(actual)
        has_condition_diff = not _is_good_condition(mic.condition)

        if has_qty_diff or has_condition_diff:
            unit_price = mic.unit_price or 0
            items.append({
                'name':       mic.id_materials.name,
                'series':     '',
                'unit':       mic.id_materials.unit_of_measurement,
                'price':      unit_price,
                'qty_doc':    planned,
                'qty_actual': actual,
                'sum_doc':    round(planned * unit_price, 2),
                'sum_actual': round(actual * unit_price, 2),
                'condition':  mic.condition or '',
            })
    return items


class DeliveryViewSet(viewsets.ModelViewSet):
    serializer_class = DeliverySerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'alerts', 'pending_today'):
            return [HasAnyRole(ACCOUNTANT, *_DELIVERY_ROLES)()]
        return [HasAnyRole(*_DELIVERY_ROLES)()]

    def get_queryset(self):
        qs = Delivery.objects.all().select_related('id_contract', 'id_act_of_arrival')
        _auto_delay(qs)
        return qs

    @action(detail=False, methods=['get'])
    def alerts(self, request):
        today = timezone.now().date()
        three_days_ago = today - timedelta(days=3)
        qs = self.get_queryset()
        overdue = qs.filter(
            status__in=[DeliveryStatus.IN_TRANSIT, DeliveryStatus.PENDING, DeliveryStatus.DELAYED],
            delivery_date__lt=three_days_ago
        )
        unaccepted = ActOfArrival.objects.filter(acceptanceofdelivery__isnull=True)
        return Response({
            "overdue_count": overdue.count(),
            "unaccepted_acts_count": unaccepted.count(),
        })

    @action(detail=False, methods=['get'])
    def pending_today(self, request):
        today = timezone.now().date()
        qs = self.get_queryset().filter(
            delivery_date=today,
            status__in=[DeliveryStatus.PENDING, DeliveryStatus.IN_TRANSIT, DeliveryStatus.NOT_DELIVERED]
        )
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def set_arrived(self, request, pk=None):
        delivery = self.get_object()
        if delivery.id_contract.status != Contract.STATUS_SIGNED:
            return Response(
                {'error': f"Действие доступно только для договоров в статусе '{Contract.STATUS_SIGNED}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        delivery.status = DeliveryStatus.DELIVERED
        delivery.save(update_fields=['status'])
        try:
            from notifications.utils import create_notification_for_role
            create_notification_for_role(
                'storekeeper',
                f"Доставка #{delivery.pk} прибыла. Необходима приёмка.",
                'info',
                '/delivery',
            )
        except Exception as e:
            logger.warning(f"Ошибка уведомления: {e}")
        return Response({'status': f'Поставка #{pk} отмечена как доставленная'})


class ActOfArrivalViewSet(viewsets.ModelViewSet):
    queryset = ActOfArrival.objects.all()
    serializer_class = ActOfArrivalSerializer

    def get_permissions(self):
        return [HasAnyRole(*_DELIVERY_ROLES)()]

    def _get_delivery(self, act):
        return Delivery.objects.filter(id_act_of_arrival=act).select_related('id_contract').first()

    def _ensure_contract_signed(self, delivery):
        if not delivery:
            return Response({'error': 'Для акта не найдена связанная поставка.'}, status=status.HTTP_400_BAD_REQUEST)
        if delivery.id_contract.status != Contract.STATUS_SIGNED:
            return Response(
                {'error': f"Действие доступно только для договоров в статусе '{Contract.STATUS_SIGNED}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def _save_items(self, delivery, items):
        if not items:
            return

        contract_material_ids = set(
            MaterialsInContract.objects.filter(id_contract=delivery.id_contract).values_list('id_materials_id', flat=True)
        )

        for item in items:
            mat_id = item.get('material_id')
            if mat_id not in contract_material_ids:
                raise ValueError(f"Материал {mat_id} отсутствует в договоре #{delivery.id_contract_id}.")

            if 'actual_quantity' not in item:
                raise ValueError(f"Для материала {mat_id} необходимо передать actual_quantity.")

            actual_qty = item.get('actual_quantity')
            if actual_qty is None or float(actual_qty) < 0:
                raise ValueError(f"actual_quantity для материала {mat_id} должен быть >= 0.")

            cond = item.get('condition', '')
            MaterialsInContract.objects.filter(
                id_contract=delivery.id_contract,
                id_materials_id=mat_id,
            ).update(actual_quantity=actual_qty, condition=cond)

    def _materials_response(self, delivery):
        materials_qs = MaterialsInContract.objects.filter(
            id_contract=delivery.id_contract
        ).select_related('id_materials')

        payload = [
            {
                'material_id': m.id_materials_id,
                'material_name': m.id_materials.name,
                'unit': m.id_materials.unit_of_measurement,
                'contract_quantity': m.materials_quality_in_contract,
                'actual_quantity': m.actual_quantity,
                'condition': m.condition,
                'unit_price': m.unit_price,
            }
            for m in materials_qs
        ]
        return payload

    @action(detail=False, methods=['get'])
    def without_acceptance(self, request):
        qs = self.queryset.filter(acceptanceofdelivery__isnull=True)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['get'])
    @extend_schema(
        description='Материалы договора по акту прибытия для модального окна приемки.'
    )
    def materials(self, request, pk=None):
        act = self.get_object()
        delivery = self._get_delivery(act)
        err = self._ensure_contract_signed(delivery)
        if err:
            return err

        return Response({
            'act_id': act.id_act_of_arrival,
            'delivery_id': delivery.id_delivery,
            'contract_id': delivery.id_contract_id,
            'items': self._materials_response(delivery),
        })

    @action(detail=False, methods=['get'], url_path='materials-by-delivery')
    @extend_schema(
        description='Материалы договора по delivery_id для модального окна приемки.'
    )
    def materials_by_delivery(self, request):
        delivery_id = request.query_params.get('delivery_id')
        if not delivery_id:
            return Response({'error': 'Параметр delivery_id обязателен.'}, status=status.HTTP_400_BAD_REQUEST)

        delivery = Delivery.objects.filter(id_delivery=delivery_id).select_related('id_contract', 'id_act_of_arrival').first()
        if not delivery:
            return Response({'error': 'Поставка не найдена.'}, status=status.HTTP_404_NOT_FOUND)

        err = self._ensure_contract_signed(delivery)
        if err:
            return err

        return Response({
            'act_id': delivery.id_act_of_arrival_id,
            'delivery_id': delivery.id_delivery,
            'contract_id': delivery.id_contract_id,
            'items': self._materials_response(delivery),
        })

    @action(detail=True, methods=['post'])
    @extend_schema(
        request=StartReceivingRequestSerializer,
        description='Начать оформление приемки и сохранить фактические количества/состояние.'
    )
    def start_receiving(self, request, pk=None):
        """Начать оформление приемки и сохранить введенные фактические данные (если переданы)."""
        act = self.get_object()
        delivery = self._get_delivery(act)
        err = self._ensure_contract_signed(delivery)
        if err:
            return err

        serializer = StartReceivingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        items = payload.get('items', [])
        storekeeper_id = payload.get('storekeeper_id')
        try:
            self._save_items(delivery, items)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if storekeeper_id:
            AcceptanceOfDelivery.objects.get_or_create(
                id_storekeeper_id=storekeeper_id,
                id_act_of_arrival=act,
            )

        act.status = DeliveryStatus.RECEIVING
        act.save(update_fields=['status'])
        return Response(self.get_serializer(act).data)

    @action(detail=True, methods=['post'])
    @extend_schema(
        request=ConfirmAcceptanceRequestSerializer,
        description='Подтверждение приемки с сохранением фактических данных и генерацией PDF актов.'
    )
    def confirm_acceptance(self, request, pk=None):
        """
        Подтверждение приемки.
        Body: { storekeeper_id: N, items: [{material_id, actual_quantity, condition}, ...] }
        """
        act = self.get_object()
        delivery = self._get_delivery(act)
        err = self._ensure_contract_signed(delivery)
        if err:
            return err

        storekeeper_id = request.data.get('storekeeper_id')
        items = request.data.get('items', [])

        if not storekeeper_id:
            return Response({'error': 'storekeeper_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self._save_items(delivery, items)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        acceptance, _ = AcceptanceOfDelivery.objects.get_or_create(
            id_storekeeper_id=storekeeper_id,
            id_act_of_arrival=act,
        )

        act.status = DeliveryStatus.RECEIVED

        materials_qs = MaterialsInContract.objects.filter(id_contract=delivery.id_contract).select_related('id_materials')

        arrival_pdf = None
        try:
            arrival_pdf = generate_arrival_pdf(act, delivery)
            act.acceptance_pdf_path = arrival_pdf.relative_path
        except Exception as exc:
            logger.error("Ошибка генерации PDF акта приемки #%s: %s", act.pk, exc, exc_info=True)

        divergence_items = _build_divergence_items(materials_qs)
        divergence_pdf = None
        if divergence_items:
            try:
                divergence_pdf = generate_divergence_pdf(act, delivery, divergence_items)
                act.divergence_pdf_path = divergence_pdf.relative_path
            except Exception as exc:
                logger.error("Ошибка генерации PDF акта расхождений #%s: %s", act.pk, exc, exc_info=True)

        act.save(update_fields=['status', 'acceptance_pdf_path', 'divergence_pdf_path'])

        try:
            works_qs = Works.objects.filter(id_storekeeper_id=storekeeper_id)
            if works_qs.exists():
                warehouse = works_qs.first().id_warehouse
                for mic in materials_qs:
                    qty = mic.actual_quantity or 0
                    if qty <= 0:
                        continue
                    inv, _ = Inventory.objects.get_or_create(
                        id_warehouse=warehouse,
                        id_materials=mic.id_materials,
                        defaults={'quantity': 0}
                    )
                    inv.quantity += qty
                    inv.save(update_fields=['quantity'])

                _check_min_stock_notifications(materials_qs)
        except Exception as e:
            logger.error(f"Ошибка обновления остатков: {e}", exc_info=True)

        try:
            from notifications.utils import create_notification_for_role
            create_notification_for_role(
                'manager',
                f"Акт прихода #{act.pk} подтверждён. Материалы добавлены на склад.",
                'info',
                '/delivery',
            )
        except Exception as e:
            logger.warning(f"Ошибка уведомления: {e}")

        return Response({
            'status': 'accepted',
            'acceptance_id': acceptance.pk,
            'act_status': act.status,
            'acceptance_pdf': {
                'filename': (arrival_pdf.filename if arrival_pdf else None),
                'file_url': (arrival_pdf.file_url if arrival_pdf else None),
            },
            'divergence_pdf': {
                'generated': bool(divergence_pdf),
                'filename': divergence_pdf.filename if divergence_pdf else None,
                'file_url': divergence_pdf.file_url if divergence_pdf else None,
            },
            'divergence_items_count': len(divergence_items),
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика по актам прибытия за период (фильтрация по дате доставки)."""
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        qs = self.queryset

        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                qs = qs.filter(delivery__delivery_date__gte=from_date_obj)
            except ValueError:
                pass
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                qs = qs.filter(delivery__delivery_date__lte=to_date_obj)
            except ValueError:
                pass

        total = qs.count()
        by_status = qs.values('status').annotate(count=Count('id_act_of_arrival'))
        status_counts = {item['status']: item['count'] for item in by_status}
        response_data = {
            'total': total,
            **status_counts
        }
        return Response(response_data)

def _check_min_stock_notifications(materials_qs):
    """Создает уведомления если остаток упал ниже минимума."""
    try:
        from notifications.utils import create_notification_for_role
        for mic in materials_qs:
            mat = mic.id_materials
            if mat.min_quantity is None:
                continue
            total = Inventory.objects.filter(id_materials=mat).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            if total < mat.min_quantity:
                create_notification_for_role(
                    'storekeeper',
                    f"Остаток материала '{mat.name}' ({total}) ниже минимума ({mat.min_quantity})",
                    'warning',
                    '/main-actions',
                )
    except Exception as e:
        logger.error(f"Ошибка проверки min_stock: {e}")


class AcceptanceOfDeliveryViewSet(viewsets.ModelViewSet):
    queryset = AcceptanceOfDelivery.objects.all().select_related('id_storekeeper', 'id_act_of_arrival')
    serializer_class = AcceptanceOfDeliverySerializer

    def get_permissions(self):
        return [HasAnyRole(*_DELIVERY_ROLES)()]

