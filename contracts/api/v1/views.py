import os
import uuid
import logging
from pathlib import Path
from datetime import timedelta

from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from django.db.models import Count, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ...models import Concluded, Contract, MaterialsInContract
from .serializers import ConcludedSerializer, ContractSerializer, MaterialsInContractSerializer
from ...utils.docx_to_pdf import convert_docx_to_pdf

# Настройка логирования для вывода в консоль
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ConcludedViewSet(ModelViewSet):
    """Заключенные договоры"""
    queryset = Concluded.objects.all().select_related(
        'id_supplier', 'id_accountant', 'id_manager', 'id_director', 'id_contract'
    ).prefetch_related('id_contract__materialsincontract_set__id_materials')
    
    serializer_class = ConcludedSerializer

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        logger.info("Запрос статистики заключённых договоров")
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)
        total_count = self.queryset.count()
        total_cost = self.queryset.aggregate(total=Sum('cost'))['total'] or 0
        recent_count = self.queryset.filter(conclusion_dates__gte=month_ago).count()
        overdue_payment = self.queryset.filter(payment_date__lt=today).count()

        logger.info(
            f"Статистика: всего={total_count}, сумма={total_cost}, "
            f"за месяц={recent_count}, просрочка={overdue_payment}"
        )
        return Response({
            "total_contracts": total_count,
            "total_cost": total_cost,
            "recent_contracts_month": recent_count,
            "overdue_payment_count": overdue_payment
        })

    @action(detail=False, methods=['get'])
    def by_manager(self, request):
        logger.info("Запрос группировки договоров по менеджерам")
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
        logger.info(f"Найдено записей по менеджерам: {len(result)}")
        return Response(result)


class ContractViewSet(ModelViewSet):
    """База контракта"""
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        """Смена статуса договора: draft / review / active / closed"""
        contract = self.get_object()
        new_status = request.data.get('status')
        allowed = ['draft', 'review', 'active', 'closed']
        if new_status not in allowed:
            return Response({'error': 'Недопустимый статус. Допустимые: ' + ', '.join(allowed)}, status=status.HTTP_400_BAD_REQUEST)
        contract.status = new_status
        contract.save()
        return Response({'id_contract': contract.id_contract, 'status': contract.status})

    @action(detail=True, methods=['get'])
    def materials_summary(self, request, pk=None):
        logger.info(f"Запрос сводки по материалам для контракта ID={pk}")
        contract = self.get_object()
        materials_qs = MaterialsInContract.objects.filter(id_contract=contract)
        serializer = MaterialsInContractSerializer(materials_qs, many=True)
        total_quantity = sum(m['actual_quantity'] for m in serializer.data)
        logger.info(
            f"Контракт {pk}: материалов={materials_qs.count()}, "
            f"общее количество={total_quantity}"
        )
        return Response({
            "contract_id": contract.id_contract,
            "materials_count": materials_qs.count(),
            "total_quantity": total_quantity,
            "details": serializer.data
        })

    @action(detail=True, methods=['get'], url_path='file/download')
    def download_file(self, request, pk=None):
        """Скачивание файла договора по ID"""
        logger.info(f"Запрос на скачивание файла для контракта ID={pk}")
        try:
            contract = Contract.objects.get(id_contract=pk)
        except Contract.DoesNotExist:
            logger.error(f"Контракт ID={pk} не найден")
            return Response({"error": "Договор не найден"}, status=status.HTTP_404_NOT_FOUND)

        if not contract.file_path:
            logger.error(f"У контракта ID={pk} нет прикреплённого файла")
            return Response({"error": "Файл не прикреплён"}, status=status.HTTP_404_NOT_FOUND)

        file_path = Path(settings.MEDIA_ROOT) / contract.file_path
        
        if not file_path.exists():
            logger.error(f"Файл {file_path} не существует на сервере")
            return Response({"error": "Файл не найден на сервере"}, status=status.HTTP_404_NOT_FOUND)

        inline = request.query_params.get('inline', 'false').lower() == 'true'
        logger.info(f"Отправка файла {file_path}, inline={inline}")
        
        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=not inline,
            filename=Path(contract.file_path).name,
            content_type='application/pdf'
        )


class MaterialsInContractViewSet(ModelViewSet):
    """Материалы в договоре"""
    queryset = MaterialsInContract.objects.all().select_related('id_materials', 'id_contract')
    serializer_class = MaterialsInContractSerializer

    @action(detail=False, methods=['get'])
    def by_contract(self, request):
        contract_id = request.query_params.get('contract_id')
        logger.info(f"Запрос материалов для контракта contract_id={contract_id}")
        if not contract_id:
            logger.error("Параметр contract_id не передан")
            return Response({"error": "Параметр contract_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)
        qs = self.queryset.filter(id_contract_id=contract_id)
        logger.info(f"Найдено записей: {qs.count()}")
        return Response(self.get_serializer(qs, many=True).data)


class ContractDocumentViewSet(viewsets.ViewSet):
    STORAGE_DIR_NAME = 'contracts_docs'

    def _get_storage_path(self):
        return Path(settings.MEDIA_ROOT) / self.STORAGE_DIR_NAME

    @action(detail=False, methods=['post'])
    def upload_docx(self, request):
        """Принимает DOCX, конвертирует в PDF, создаёт запись Contract с file_path"""
        logger.info("Начало загрузки DOCX файла")
        file_obj = request.FILES.get('file')
        if not file_obj:
            logger.error("Файл не передан")
            return Response({"error": "Файл не передан"}, status=status.HTTP_400_BAD_REQUEST)

        if not file_obj.name.lower().endswith('.docx'):
            logger.error(f"Неверный формат файла: {file_obj.name}")
            return Response({"error": "Требуется файл .docx"}, status=status.HTTP_400_BAD_REQUEST)

        storage_path = self._get_storage_path()
        storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Папка для хранения: {storage_path}")

        unique_id = uuid.uuid4().hex
        original_name = Path(file_obj.name).stem
        pdf_filename = f"{unique_id}_{original_name}.pdf"
        output_pdf = storage_path / pdf_filename

        temp_docx = storage_path / f"temp_{unique_id}.docx"
        logger.info(f"Сохраняем временный DOCX: {temp_docx}")
        with open(temp_docx, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        logger.info("Временный файл сохранён")

        try:
            logger.info("Запуск конвертации DOCX -> PDF")
            convert_docx_to_pdf(temp_docx, output_pdf)
            logger.info(f"Конвертация завершена, PDF сохранён: {output_pdf}")
            
            contract = Contract.objects.create(
                file_path=f"{self.STORAGE_DIR_NAME}/{pdf_filename}"
            )
            logger.info(f"Создана запись Contract с ID={contract.id_contract}")
            
            temp_docx.unlink(missing_ok=True)
            logger.info("Временный DOCX удалён")
            
            return Response({
                "status": "success",
                "contract_id": contract.id_contract,
                "filename": pdf_filename,
                "path": str(output_pdf)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке файла: {e}", exc_info=True)
            temp_docx.unlink(missing_ok=True)
            if output_pdf.exists():
                output_pdf.unlink()
                logger.info("Неудавшийся PDF удалён")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def list_files(self, request):
        """
        Возвращает список доступных PDF файлов в папке.
        """
        logger.info("Запрос списка PDF файлов")
        storage_path = self._get_storage_path()
        if not storage_path.exists():
            logger.info("Папка с файлами не существует")
            return Response([])

        files = [f.name for f in storage_path.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
        logger.info(f"Найдено файлов: {len(files)}")
        return Response({"files": files})

    @action(detail=False, methods=['get'], url_path='download')
    def download_file(self, request):
        """Скачивание файла по имени."""
        filename = request.query_params.get('filename')
        inline = request.query_params.get('inline', 'false').lower() == 'true'
        logger.info(f"Запрос на скачивание файла: {filename}, inline={inline}")
        
        if not filename:
            logger.error("Не передан параметр filename")
            return Response({"error": "Параметр filename обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        if '..' in filename or filename.startswith('/'):
            logger.error(f"Некорректное имя файла: {filename}")
            return Response({"error": "Некорректное имя файла"}, status=status.HTTP_400_BAD_REQUEST)

        storage_path = self._get_storage_path()
        file_path = storage_path / filename

        try:
            file_path.resolve().relative_to(storage_path.resolve())
        except ValueError:
            logger.error(f"Попытка доступа к файлу вне разрешённой директории: {file_path}")
            return Response({"error": "Доступ запрещен"}, status=status.HTTP_403_FORBIDDEN)

        if not file_path.exists():
            logger.error(f"Файл не найден: {file_path}")
            return Response({"error": "Файл не найден"}, status=status.HTTP_404_NOT_FOUND)

        logger.info(f"Отправка файла: {file_path}")
        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=not inline,
            filename=filename,
            content_type='application/pdf'
        )
