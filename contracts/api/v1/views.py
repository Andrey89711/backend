import os
from pathlib import Path
from django.conf import settings
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count

from rest_framework.viewsets import ModelViewSet 
from ...models import Concluded, Contract, MaterialsInContract
from .serializers import ConcludedSerializer, ContractSerializer, MaterialsInContractSerializer
from ...utils.docx_to_pdf import convert_docx_to_pdf

class ConcludedViewSet(ModelViewSet):
    """Заключенные договоры"""
    queryset = Concluded.objects.all().select_related(
        'id_supplier', 'id_accountant', 'id_manager', 'id_director', 'id_contract'
    ).prefetch_related('id_contract__materialsincontract_set__id_materials')
    
    serializer_class = ConcludedSerializer

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)
        total_count = self.queryset.count()
        total_cost = self.queryset.aggregate(total=Sum('cost'))['total'] or 0
        recent_count = self.queryset.filter(conclusion_dates__gte=month_ago).count()
        overdue_payment = self.queryset.filter(payment_date__lt=today).count()

        return Response({
            "total_contracts": total_count,
            "total_cost": total_cost,
            "recent_contracts_month": recent_count,
            "overdue_payment_count": overdue_payment
        })

    @action(detail=False, methods=['get'])
    def by_manager(self, request):
        data = self.queryset.values('id_manager__full_name', 'id_manager__id').annotate(
            count=Count('id_contract'), total_cost=Sum('cost')
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

class ContractViewSet(ModelViewSet):
    """База контракта"""
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer

    @action(detail=True, methods=['get'])
    def materials_summary(self, request, pk=None):
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

class MaterialsInContractViewSet(ModelViewSet):
    """Материалы в договоре"""
    queryset = MaterialsInContract.objects.all().select_related('id_materials', 'id_contract')
    serializer_class = MaterialsInContractSerializer

    @action(detail=False, methods=['get'])
    def by_contract(self, request):
        contract_id = request.query_params.get('contract_id')
        if not contract_id:
            return Response({"error": "Параметр contract_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)
        qs = self.queryset.filter(id_contract_id=contract_id)
        return Response(self.get_serializer(qs, many=True).data)

class ContractDocumentViewSet(viewsets.ViewSet):
    """
    Работа с файлами договоров (Загрузка DOCX -> PDF, Список, Скачивание).
    Файлы хранятся в MEDIA_ROOT/contracts_docs/
    """
    # Папка для хранения PDF внутри MEDIA_ROOT
    STORAGE_DIR_NAME = 'contracts_docs'

    def _get_storage_path(self):
        return Path(settings.MEDIA_ROOT) / self.STORAGE_DIR_NAME

    @action(detail=False, methods=['post'])
    def upload_docx(self, request):
        """
        Принимает DOCX, конвертирует в PDF и сохраняет.
        Возвращает имя сохраненного PDF файла.
        """
        print(f"[DEBUG] Content-Type: {request.content_type}")  # Должно быть multipart...
        print(f"[DEBUG] FILES: {request.FILES}")
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Файл не передан"}, status=status.HTTP_400_BAD_REQUEST)

        if not file_obj.name.lower().endswith('.docx'):
            return Response({"error": "Требуется файл .docx"}, status=status.HTTP_400_BAD_REQUEST)

        storage_path = self._get_storage_path()
        storage_path.mkdir(parents=True, exist_ok=True)

        # Временное сохранение DOCX
        temp_docx = storage_path / f"temp_{file_obj.name}"
        with open(temp_docx, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        # Имя выходного PDF (можно генерировать уникальное, пока оставляем имя исходного)
        pdf_filename = f"{file_obj.name[:-5]}.pdf" # заменяем .docx на .pdf
        output_pdf = storage_path / pdf_filename

        try:
            convert_docx_to_pdf(temp_docx, output_pdf)
            # Удаляем временный DOCX после успеха
            temp_docx.unlink(missing_ok=True)
            return Response({
            "status": "success", 
            "filename": pdf_filename,
            "path": str(output_pdf)
        }, status=status.HTTP_201_CREATED)
        except Exception as e:
            # Удаляем мусор при ошибке
            temp_docx.unlink(missing_ok=True)
            output_pdf.unlink(missing_ok=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def list_files(self, request):
        """
        Возвращает список доступных PDF файлов в папке.
        """
        storage_path = self._get_storage_path()
        if not storage_path.exists():
            return Response([])

        files = [f.name for f in storage_path.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
        return Response({"files": files})

    @action(detail=False, methods=['get'], url_path='download')
    def download_file(self, request):
        """
        Скачивание файла по имени.
        Пример: /api/contracts/documents/download/?filename=dogovor.pdf
        """
        filename = request.query_params.get('filename')
        inline = request.query_params.get('inline', 'false').lower() == 'true'
        if not filename:
            return Response({"error": "Параметр filename обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        # Защита от выхода за пределы директории (Directory Traversal)
        if '..' in filename or filename.startswith('/'):
            return Response({"error": "Некорректное имя файла"}, status=status.HTTP_400_BAD_REQUEST)

        storage_path = self._get_storage_path()
        file_path = storage_path / filename

        # Проверка, что файл реально лежит внутри нашей папки
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