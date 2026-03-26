import logging
import re
import tempfile
import uuid

from datetime import timedelta
from pathlib import Path
from datetime import datetime
from docxtpl import DocxTemplate
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import AccessToken
from drf_spectacular.utils import extend_schema

from contracts.models import Concluded, Contract, MaterialsInContract
from contracts.services.documents import PdfDocumentService, generate_contract_pdf
from contracts.services.pricing import (
    PriceResolutionError,
    is_material_available_for_supplier,
    resolve_unit_price_for_material,
)
from contracts.utils.docx_to_pdf import convert_docx_to_pdf
from .serializers import (
    ConcludedSerializer,
    ContractSerializer,
    MaterialsInContractSerializer,
    SetContractStatusSerializer,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _normalize_template_payload(data):
    """
    Normalize client payload keys to snake_case and keep backward-compatible aliases.
    """
    aliases = {
        'contract_number': ['contractnumber'],
        'contract_date': ['contractdate'],
        'buyer_name': ['buyername'],
        'buyer_director': ['buyerdirector'],
        'buyer_basis': ['buyerbasis'],
        'supplier_name': ['suppliername'],
        'supplier_full_name': ['supplierfullname'],
        'supplier_short_name': ['suppliershortname'],
        'supplier_inn': ['supplierinn'],
        'supplier_address': ['supplieraddress'],
        'supplier_director': ['supplierdirector'],
        'supplier_director_position': ['supplierdirectorposition'],
        'supplier_basis': ['supplierbasis'],
        'invoice_number': ['invoicenumber'],
        'place_of_contract': ['placeofcontract'],
        'current_date': ['currentdate'],
        'delivery_frequency': ['deliveryfrequency'],
        'delivery_frequency_custom': ['deliveryfrequencycustom'],
        'delivery_schedule': ['deliveryschedule'],
        'transport_type': ['transporttype'],
        'payment_term': ['paymentterm'],
        'penalty_shortage': ['penaltyshortage'],
        'penalty_late_payment': ['penaltylatepayment'],
        'contract_end_date': ['contractenddate'],
        'renewal_term': ['renewalterm'],
        'price_without_vat': ['pricewithoutvat'],
        'price_with_vat': ['pricewithvat'],
        'total_amount': ['totalamount'],
        'total_amount_words': ['totalamountwords'],
        'total_quantity': ['totalquantity'],
        'qty_doc': ['qtydoc'],
        'sum_doc': ['sumdoc'],
        'qty_actual': ['qtyactual'],
        'sum_actual': ['sumactual'],
        'organization_name': ['organizationname'],
        'organization_address': ['organizationaddress'],
        'act_date': ['actdate'],
        'act_place': ['actplace'],
        'commission_members': ['commissionmembers'],
        'representative_name': ['representativename'],
        'certificate_number': ['certificatenumber'],
        'certificate_date': ['certificatedate'],
        'sender_name': ['sendername'],
        'carrier_name': ['carriername'],
        'invoice_date': ['invoicedate'],
        'sign_date': ['signdate'],
        'sign_name': ['signname'],
    }

    if isinstance(data, dict):
        normalized = {}
        for key, value in data.items():
            snake_key = _camel_to_snake(key)
            normalized[snake_key] = _normalize_template_payload(value)
        # add aliases for templates that still use old placeholders
        lower_keys_map = {k.lower().replace('_', ''): k for k in normalized.keys()}
        for canonical, alias_keys in aliases.items():
            if canonical in normalized:
                continue
            for alias in alias_keys:
                source_key = lower_keys_map.get(alias)
                if source_key:
                    normalized[canonical] = normalized[source_key]
                    break
        return normalized
    if isinstance(data, list):
        return [_normalize_template_payload(item) for item in data]
    return data


def _summarize_context(data):
    summary = {}
    for key, value in (data or {}).items():
        if isinstance(value, list):
            summary[key] = {'type': 'list', 'size': len(value)}
        elif isinstance(value, dict):
            summary[key] = {'type': 'dict', 'keys': sorted(value.keys())}
        else:
            summary[key] = type(value).__name__
    return summary




def _recalc_cost(concluded):
    """Пересчитывает и сохраняет стоимость договора по материалам."""
    total = sum(
        (m.unit_price or 0) * (m.materials_quality_in_contract or 0)
        for m in concluded.id_contract.materialsincontract_set.all()
    )
    concluded.cost = round(total, 2)
    concluded.save(update_fields=['cost'])
    return concluded.cost


def _create_delivery_and_act(concluded):
    """Создаёт Delivery + ActOfArrival только для подписанного договора."""
    from deliveries.models import ActOfArrival, Delivery
    from deliveries.choices import DeliveryStatus

    contract = concluded.id_contract
    if contract.status != Contract.STATUS_SIGNED:
        logger.info(
            "Доставка не создана: договор #%s в статусе '%s' (нужен '%s').",
            contract.id_contract,
            contract.status,
            Contract.STATUS_SIGNED,
        )
        return None

    if Delivery.objects.filter(id_contract=contract).exists():
        return Delivery.objects.filter(id_contract=contract).first().id_act_of_arrival

    delivery_date = concluded.delivery_date or concluded.payment_date

    act = ActOfArrival.objects.create(status=DeliveryStatus.PENDING)
    Delivery.objects.create(
        status=DeliveryStatus.IN_TRANSIT,
        delivery_date=delivery_date,
        id_contract=contract,
        id_act_of_arrival=act,
    )
    logger.info(
        "Авто-создан ActOfArrival #%s и Delivery для договора #%s",
        act.pk,
        concluded.id_contract_id,
    )
    return act


def _ensure_delivery_created_for_signed_contract(contract: Contract):
    """Создает delivery/act при переходе договора в signed (если есть concluded и еще нет доставки)."""
    if contract.status != Contract.STATUS_SIGNED:
        return
    if not hasattr(contract, 'concluded'):
        return

    from deliveries.models import Delivery

    if Delivery.objects.filter(id_contract=contract).exists():
        return
    _create_delivery_and_act(contract.concluded)


class ConcludedViewSet(ModelViewSet):
    queryset = Concluded.objects.all().select_related(
        'id_supplier', 'id_accountant', 'id_manager', 'id_director', 'id_contract'
    ).prefetch_related('id_contract__materialsincontract_set__id_materials')

    serializer_class = ConcludedSerializer

    def perform_create(self, serializer):
        concluded = serializer.save()
        _create_delivery_and_act(concluded)
        try:
            from notifications.utils import create_notification_for_role
            create_notification_for_role(
                'manager',
                f"Создан заключённый договор #{concluded.id_contract_id} с поставщиком {concluded.id_supplier.name}",
                'info',
                '/main-actions',
            )
        except Exception as e:
            logger.warning(f"Ошибка отправки уведомления: {e}")

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Отметить договор как оплаченный и списать баланс предприятия."""
        concluded = self.get_object()
        if concluded.is_paid:
            return Response({'detail': 'Договор уже оплачен.'}, status=status.HTTP_400_BAD_REQUEST)

        concluded.is_paid = True
        concluded.save(update_fields=['is_paid'])

        try:
            from finance.models import EnterpriseBalance
            balance = EnterpriseBalance.objects.first()
            if balance:
                balance.amount = float(balance.amount) - concluded.cost
                balance.save(update_fields=['amount'])
        except Exception as e:
            logger.warning(f"Ошибка списания баланса: {e}")

        return Response({'id_contract': concluded.id_contract_id, 'is_paid': True, 'cost': concluded.cost})

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)
        qs = self.queryset
        total_count = qs.count()
        total_cost = qs.aggregate(total=Sum('cost'))['total'] or 0
        recent_count = qs.filter(conclusion_dates__gte=month_ago).count()
        overdue_payment = qs.filter(payment_date__lt=today).count()
        unpaid_count = qs.filter(is_paid=False).count()
        overdue_unpaid_count = qs.filter(is_paid=False, payment_date__lt=today).count()

        return Response({
            "total_contracts": total_count,
            "total_cost": total_cost,
            "recent_contracts_month": recent_count,
            "overdue_payment_count": overdue_payment,
            "unpaid_count": unpaid_count,
            "overdue_unpaid_count": overdue_unpaid_count,
        })

    @action(detail=False, methods=['get'])
    def by_manager(self, request):
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        
        qs = self.queryset
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                qs = qs.filter(conclusion_dates__gte=from_date_obj)
            except ValueError:
                pass
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                qs = qs.filter(conclusion_dates__lte=to_date_obj)
            except ValueError:
                pass
        
        data = qs.values('id_manager__full_name', 'id_manager__id_manager').annotate(
            count=Count('id_contract'), total_cost=Sum('cost')
        )
        result = [
            {
                "manager_id": item['id_manager__id_manager'],
                "manager_name": item['id_manager__full_name'] or "Не указан",
                "contracts_count": item['count'],
                "total_cost": item['total_cost'] or 0
            }
            for item in data
        ]
        return Response(result)

class ContractViewSet(ModelViewSet):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer

    def perform_create(self, serializer):
        contract = serializer.save()
        self._generate_contract_pdf(contract)

    def perform_update(self, serializer):
        contract = serializer.save()
        self._generate_contract_pdf(contract)

    def _generate_contract_pdf(self, contract: Contract):
        try:
            generated = generate_contract_pdf(contract)
            contract.file_path = generated.relative_path
            contract.save(update_fields=['file_path'])
        except Exception as exc:
            logger.error(
                "Ошибка автогенерации PDF договора #%s: %s",
                contract.id_contract,
                exc,
                exc_info=True,
            )

    @action(detail=True, methods=['post'], url_path='set-status')
    @extend_schema(
        request=SetContractStatusSerializer,
        description='Смена статуса договора по допустимому workflow: created -> approved -> signed -> annulled.'
    )
    def set_status(self, request, pk=None):
        contract = self.get_object()
        new_status = request.data.get('status')
        allowed = [status for status, _ in Contract.STATUS_CHOICES]

        if new_status not in allowed:
            return Response(
                {'error': 'Недопустимый статус. Допустимые: ' + ', '.join(allowed)},
                status=status.HTTP_400_BAD_REQUEST
            )

        if contract.status == new_status:
            return Response({
                'id_contract': contract.id_contract,
                'status': contract.status,
                'available_next_statuses': contract.get_available_next_statuses(),
            })

        if not contract.can_transition_to(new_status):
            return Response(
                {
                    'error': (
                        f"Недопустимый переход статуса: '{contract.status}' -> '{new_status}'. "
                        f"Разрешены только: {', '.join(contract.get_available_next_statuses()) or 'нет'}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        contract.status = new_status
        contract.save(update_fields=['status'])

        if new_status == Contract.STATUS_SIGNED:
            _ensure_delivery_created_for_signed_contract(contract)

        if new_status == Contract.STATUS_ANNULLED:
            logger.info("Договор #%s переведен в 'annulled' (заглушка обработки).", contract.id_contract)
            try:
                from notifications.utils import create_notification_for_role

                create_notification_for_role(
                    'manager',
                    f"Договор #{contract.id_contract} переведен в статус annulled (заглушка).",
                    'warning',
                    '/agreement?tab=view',
                )
            except Exception as exc:
                logger.warning(f"Не удалось отправить уведомление об annulled: {exc}")

        return Response({
            'id_contract': contract.id_contract,
            'status': contract.status,
            'available_next_statuses': contract.get_available_next_statuses(),
        })

    @action(detail=True, methods=['get'])
    def materials_summary(self, request, pk=None):
        contract = self.get_object()
        materials_qs = MaterialsInContract.objects.filter(id_contract=contract)
        serializer = MaterialsInContractSerializer(materials_qs, many=True)
        total_quantity = sum(
            (m['materials_quality_in_contract'] or 0) for m in serializer.data
        )
        total_cost = sum(
            (m.get('unit_price') or 0) * (m['materials_quality_in_contract'] or 0)
            for m in serializer.data
        )
        return Response({
            "contract_id": contract.id_contract,
            "materials_count": materials_qs.count(),
            "total_quantity": total_quantity,
            "total_cost": round(total_cost, 2),
            "details": serializer.data
        })

    @action(detail=True, methods=['get'], url_path='file/download')
    def download_file(self, request, pk=None):
        try:
            contract = Contract.objects.get(id_contract=pk)
        except Contract.DoesNotExist:
            return Response({"error": "Договор не найден"}, status=status.HTTP_404_NOT_FOUND)

        if not contract.file_path:
            return Response({"error": "Файл не прикреплён"}, status=status.HTTP_404_NOT_FOUND)

        file_path = Path(settings.MEDIA_ROOT) / contract.file_path
        if not file_path.exists():
            return Response({"error": "Файл не найден на сервере"}, status=status.HTTP_404_NOT_FOUND)

        token = request.query_params.get('token')
        if token:
            try:
                AccessToken(token)
            except Exception:
                return Response({"error": "Неверный или просроченный токен"}, status=status.HTTP_401_UNAUTHORIZED)
        elif not request.user.is_authenticated:
            return Response({"error": "Учетные данные не были предоставлены."}, status=status.HTTP_401_UNAUTHORIZED)

        inline = request.query_params.get('inline', 'false').lower() == 'true'
        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=not inline,
            filename=Path(contract.file_path).name,
            content_type='application/pdf'
        )


class MaterialsInContractViewSet(ModelViewSet):
    queryset = MaterialsInContract.objects.all().select_related('id_materials', 'id_contract')
    serializer_class = MaterialsInContractSerializer

    def perform_create(self, serializer):
        contract = serializer.validated_data['id_contract']
        material = serializer.validated_data['id_materials']
        incoming_price = serializer.validated_data.get('unit_price')
        if not is_material_available_for_supplier(contract, material.id_materials):
            supplier_name = contract.concluded.id_supplier.name if hasattr(contract, 'concluded') else None
            raise PriceResolutionError({
                'id_materials': (
                    f"Материал недоступен у поставщика '{supplier_name}'. "
                    "Выберите материал с ценой у поставщика договора."
                )
            })

        try:
            unit_price = resolve_unit_price_for_material(
                contract=contract,
                material_id=material.id_materials,
                unit_price=incoming_price,
            )
        except PriceResolutionError as exc:
            raise exc

        instance = serializer.save(unit_price=unit_price)
        try:
            concluded = instance.id_contract.concluded
            _recalc_cost(concluded)
        except Concluded.DoesNotExist:
            pass

    def perform_update(self, serializer):
        instance = serializer.instance
        contract = serializer.validated_data.get('id_contract', instance.id_contract)
        material = serializer.validated_data.get('id_materials', instance.id_materials)
        incoming_price = serializer.validated_data.get('unit_price', instance.unit_price)
        if not is_material_available_for_supplier(contract, material.id_materials):
            supplier_name = contract.concluded.id_supplier.name if hasattr(contract, 'concluded') else None
            raise PriceResolutionError({
                'id_materials': (
                    f"Материал недоступен у поставщика '{supplier_name}'. "
                    "Выберите материал с ценой у поставщика договора."
                )
            })

        if incoming_price is None or incoming_price <= 0:
            unit_price = resolve_unit_price_for_material(
                contract=contract,
                material_id=material.id_materials,
                unit_price=None,
            )
        else:
            unit_price = round(float(incoming_price), 2)

        updated = serializer.save(unit_price=unit_price)
        try:
            concluded = updated.id_contract.concluded
            _recalc_cost(concluded)
        except Concluded.DoesNotExist:
            pass

    def perform_destroy(self, instance):
        contract = instance.id_contract
        instance.delete()
        try:
            concluded = contract.concluded
            _recalc_cost(concluded)
        except Concluded.DoesNotExist:
            pass

    @action(detail=False, methods=['get'])
    def by_contract(self, request):
        contract_id = request.query_params.get('contract_id')
        if not contract_id:
            return Response({"error": "Параметр contract_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)
        qs = self.queryset.filter(id_contract_id=contract_id)
        return Response(self.get_serializer(qs, many=True).data)


class ContractDocumentViewSet(viewsets.ViewSet):
    STORAGE_DIR_NAME = 'contracts_docs'
    TEMPLATE_DIR = Path(settings.BASE_DIR) / 'contracts_templates'

    def _get_storage_path(self):
        return Path(settings.MEDIA_ROOT) / self.STORAGE_DIR_NAME

    @action(detail=False, methods=['post'])
    def upload_docx(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Файл не передан"}, status=status.HTTP_400_BAD_REQUEST)
        if not file_obj.name.lower().endswith('.docx'):
            return Response({"error": "Требуется файл .docx"}, status=status.HTTP_400_BAD_REQUEST)

        storage_path = self._get_storage_path()
        storage_path.mkdir(parents=True, exist_ok=True)

        unique_id = uuid.uuid4().hex
        original_name = Path(file_obj.name).stem
        pdf_filename = f"{unique_id}_{original_name}.pdf"
        output_pdf = storage_path / pdf_filename
        temp_docx = storage_path / f"temp_{unique_id}.docx"

        with open(temp_docx, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        try:
            convert_docx_to_pdf(temp_docx, output_pdf)
            contract = Contract.objects.create(file_path=f"{self.STORAGE_DIR_NAME}/{pdf_filename}")
            temp_docx.unlink(missing_ok=True)
            try:
                from notifications.utils import create_notification_for_role

                create_notification_for_role(
                    'manager',
                    f"Создан документ договора #{contract.id_contract}",
                    'info',
                    '/agreement?tab=view',
                )
            except Exception as ne:
                logger.warning(f"Ошибка отправки уведомления: {ne}")
            return Response({
                "status": "success",
                "contract_id": contract.id_contract,
                "filename": pdf_filename,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Ошибка при обработке файла: {e}", exc_info=True)
            temp_docx.unlink(missing_ok=True)
            if output_pdf.exists():
                output_pdf.unlink()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def list_files(self, request):
        storage_path = self._get_storage_path()
        if not storage_path.exists():
            return Response([])
        files = [f.name for f in storage_path.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
        return Response({"files": files})

    @action(detail=False, methods=['get'], url_path='download')
    def download_file(self, request):
        filename = request.query_params.get('filename')
        inline = request.query_params.get('inline', 'false').lower() == 'true'
        if not filename:
            return Response({"error": "Параметр filename обязателен"}, status=status.HTTP_400_BAD_REQUEST)
        if '..' in filename or filename.startswith('/'):
            return Response({"error": "Некорректное имя файла"}, status=status.HTTP_400_BAD_REQUEST)

        storage_path = self._get_storage_path()
        file_path = storage_path / filename

        try:
            file_path.resolve().relative_to(storage_path.resolve())
        except ValueError:
            return Response({"error": "Доступ запрещен"}, status=status.HTTP_403_FORBIDDEN)

        if not file_path.exists():
            return Response({"error": "Файл не найден"}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=not inline,
            filename=filename,
            content_type='application/pdf'
        )

    @action(detail=False, methods=['post'], url_path='generate-docx')
    def generate_docx(self, request):
        template_name = request.data.get('template')
        data = _normalize_template_payload(request.data.get('data', {}))
        if not template_name:
            return Response({"error": "Параметр 'template' обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        template_path = self.TEMPLATE_DIR / template_name
        if not template_path.exists():
            return Response({"error": f"Шаблон '{template_name}' не найден"}, status=status.HTTP_404_NOT_FOUND)

        try:
            logger.debug(
                "Generate DOCX template='%s' context metadata=%s",
                template_name,
                _summarize_context(data),
            )
            doc = DocxTemplate(str(template_path))
            doc.render(data)
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
                tmp_path = Path(tmp.name)
                doc.save(tmp_path)
            with open(tmp_path, 'rb') as f:
                file_content = f.read()
            base_name = Path(template_name).stem.replace('_template', '')
            filename = f"{base_name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.docx"
            response = HttpResponse(
                file_content,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            tmp_path.unlink(missing_ok=True)
            return response
        except Exception as e:
            logger.error(f"Ошибка генерации DOCX: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='generate-pdf')
    def generate_pdf(self, request):
        template_name = request.data.get('template')
        data = _normalize_template_payload(request.data.get('data', {}))
        if not template_name:
            return Response({"error": "Параметр 'template' обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        template_path = self.TEMPLATE_DIR / template_name
        if not template_path.exists():
            return Response({"error": f"Шаблон '{template_name}' не найден"}, status=status.HTTP_404_NOT_FOUND)

        try:
            logger.debug(
                "Generate PDF template='%s' context metadata=%s",
                template_name,
                _summarize_context(data),
            )
            generated = PdfDocumentService.generate_pdf(
                template_name=template_name,
                context=data,
                base_name=Path(template_name).stem.replace('_template', ''),
            )
            contract = Contract.objects.create(file_path=generated.relative_path)
            try:
                from notifications.utils import create_notification_for_role

                create_notification_for_role(
                    'manager',
                    f"Создан документ договора #{contract.id_contract}",
                    'info',
                    '/agreement?tab=view',
                )
            except Exception as ne:
                logger.warning(f"Ошибка отправки уведомления: {ne}")

            return Response({
                "status": "success",
                "message": "Файл успешно сохранён",
                "contract_id": contract.id_contract,
                "filename": generated.filename,
                "file_url": generated.file_url,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Ошибка сохранения PDF: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

