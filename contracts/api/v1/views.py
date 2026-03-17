import os
import uuid
import logging
from pathlib import Path
from datetime import timedelta
import tempfile
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
from ...models import Concluded, Contract, MaterialsInContract
from .serializers import ConcludedSerializer, ContractSerializer, MaterialsInContractSerializer
from ...utils.docx_to_pdf import convert_docx_to_pdf

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
    """Автоматически создаёт Delivery + ActOfArrival при создании Concluded."""
    from deliveries.models import ActOfArrival, Delivery
    from deliveries.choices import DeliveryStatus

    delivery_date = concluded.delivery_date or concluded.payment_date

    act = ActOfArrival.objects.create(status=DeliveryStatus.PENDING)
    Delivery.objects.create(
        status=DeliveryStatus.IN_TRANSIT,
        delivery_date=delivery_date,
        id_contract=concluded.id_contract,
        id_act_of_arrival=act,
    )
    logger.info(
        f"Авто-создан ActOfArrival #{act.pk} и Delivery для договора #{concluded.id_contract_id}"
    )
    return act


class ConcludedViewSet(ModelViewSet):
    queryset = Concluded.objects.all().select_related(
        'id_supplier', 'id_accountant', 'id_manager', 'id_director', 'id_contract'
    ).prefetch_related('id_contract__materialsincontract_set__id_materials')

    serializer_class = ConcludedSerializer

    def perform_create(self, serializer):
        concluded = serializer.save()
        # Автоматически создаём Delivery + ActOfArrival
        _create_delivery_and_act(concluded)
        # Уведомление менеджеру
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

        # Списываем с баланса предприятия
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
        data = self.queryset.values('id_manager__full_name', 'id_manager__id_manager').annotate(
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

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        contract = self.get_object()
        new_status = request.data.get('status')
        allowed = ['draft', 'review', 'active', 'closed']
        if new_status not in allowed:
            return Response(
                {'error': 'Недопустимый статус. Допустимые: ' + ', '.join(allowed)},
                status=status.HTTP_400_BAD_REQUEST
            )
        contract.status = new_status
        contract.save()
        return Response({'id_contract': contract.id_contract, 'status': contract.status})

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
        instance = serializer.save()
        # Пересчитываем стоимость договора
        try:
            concluded = instance.id_contract.concluded
            _recalc_cost(concluded)
        except Concluded.DoesNotExist:
            pass

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            concluded = instance.id_contract.concluded
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
    TEMPLATE_DIR = Path(settings.MEDIA_ROOT) / 'contracts_templates'

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
        data = request.data.get('data', {})
        if not template_name:
            return Response({"error": "Параметр 'template' обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        template_path = self.TEMPLATE_DIR / template_name
        if not template_path.exists():
            return Response({"error": f"Шаблон '{template_name}' не найден"}, status=status.HTTP_404_NOT_FOUND)

        try:
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
        data = request.data.get('data', {})
        if not template_name:
            return Response({"error": "Параметр 'template' обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        template_path = self.TEMPLATE_DIR / template_name
        if not template_path.exists():
            return Response({"error": f"Шаблон '{template_name}' не найден"}, status=status.HTTP_404_NOT_FOUND)

        try:
            doc = DocxTemplate(str(template_path))
            doc.render(data)
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
                tmp_path = Path(tmp.name)
                doc.save(tmp_path)
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_tmp:
                pdf_path = Path(pdf_tmp.name)
            convert_docx_to_pdf(tmp_path, pdf_path)
            with open(pdf_path, 'rb') as f:
                file_content = f.read()
            storage_path = self._get_storage_path()
            storage_path.mkdir(parents=True, exist_ok=True)
            unique_id = uuid.uuid4().hex
            base_name = Path(template_name).stem.replace('_template', '')
            filename = f"{base_name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            saved_filename = f"{unique_id}_{filename}"
            saved_path = storage_path / saved_filename
            with open(saved_path, 'wb') as f:
                f.write(file_content)
            contract = Contract.objects.create(file_path=f"{self.STORAGE_DIR_NAME}/{saved_filename}")
            for path in [tmp_path, pdf_path]:
                path.unlink(missing_ok=True)
            return Response({
                "status": "success",
                "message": "Файл успешно сохранён",
                "contract_id": contract.id_contract,
                "filename": saved_filename,
                "file_url": f"/media/{self.STORAGE_DIR_NAME}/{saved_filename}"
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Ошибка сохранения PDF: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
