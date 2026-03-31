import logging
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from docxtpl import DocxTemplate
from django.conf import settings
from django.utils import timezone

from contracts.models import Contract, MaterialsInContract
from contracts.utils.docx_to_pdf import convert_docx_to_pdf

logger = logging.getLogger(__name__)


def _summarize_context(context: dict) -> dict:
    """Return safe context metadata for debug logs (no values)."""
    summary = {}
    for key, value in (context or {}).items():
        if isinstance(value, (list, tuple, set)):
            summary[key] = {'type': type(value).__name__, 'size': len(value)}
        elif isinstance(value, dict):
            summary[key] = {'type': 'dict', 'keys': sorted(value.keys())}
        else:
            summary[key] = type(value).__name__
    return summary


@dataclass
class GeneratedPdf:
    filename: str
    relative_path: str
    file_url: str


class PdfDocumentService:
    STORAGE_DIR_NAME = 'contracts_docs'
    TEMPLATE_DIR = Path(settings.BASE_DIR) / 'contracts_templates'

    @classmethod
    def get_storage_path(cls) -> Path:
        path = Path(settings.MEDIA_ROOT) / cls.STORAGE_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def build_file_url(cls, relative_path: str) -> str:
        media_url = settings.MEDIA_URL if settings.MEDIA_URL.endswith('/') else f"{settings.MEDIA_URL}/"
        return f"{media_url}{relative_path}"

    @classmethod
    def generate_pdf(cls, template_name: str, context: dict, base_name: str) -> GeneratedPdf:
        template_path = cls.TEMPLATE_DIR / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")

        logger.debug(
            "Rendering template '%s' with context metadata: %s",
            template_name,
            _summarize_context(context),
        )
        doc = DocxTemplate(str(template_path))
        doc.render(context)

        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_docx:
            docx_path = Path(tmp_docx.name)
            doc.save(docx_path)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf_path = Path(tmp_pdf.name)

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        saved_name = f"{uuid.uuid4().hex}_{base_name}_{timestamp}.pdf"
        relative_path = f"{cls.STORAGE_DIR_NAME}/{saved_name}"
        destination = cls.get_storage_path() / saved_name

        try:
            convert_docx_to_pdf(docx_path, tmp_pdf_path)
            destination.write_bytes(tmp_pdf_path.read_bytes())
        finally:
            docx_path.unlink(missing_ok=True)
            tmp_pdf_path.unlink(missing_ok=True)

        return GeneratedPdf(
            filename=saved_name,
            relative_path=relative_path,
            file_url=cls.build_file_url(relative_path),
        )


def _contract_material_rows(contract: Contract):
    rows = []
    for item in contract.materialsincontract_set.select_related('id_materials').all():
        qty = item.materials_quality_in_contract or 0
        unit_price = item.unit_price or 0
        rows.append({
            'name': item.id_materials.name,
            'unit': item.id_materials.unit_of_measurement,
            'qty': qty,
            'unit_price': unit_price,
            'sum': round(qty * unit_price, 2),
            'actual_quantity': item.actual_quantity or 0,
            'condition': item.condition or '',
        })
    return rows


def build_contract_context(contract: Contract) -> dict:
    concluded = getattr(contract, 'concluded', None)
    rows = _contract_material_rows(contract)
    total = sum(r['sum'] for r in rows)
    
    supplier   = concluded.id_supplier   if concluded else None
    director   = concluded.id_director   if concluded else None
    accountant = concluded.id_accountant if concluded else None
    manager    = concluded.id_manager    if concluded else None

    return {
        'supplier_full_name': supplier.name if supplier else 'ООО "Поставщик"',
        'supplier_name':      supplier.name if supplier else 'ООО "Поставщик"',
        'supplier_inn':       supplier.tax_id if supplier else '1234567890',
        'supplier_address':   supplier.payment_details if supplier else '123456, г. Москва, ул. Ленина, д. 1',
        'supplier_director':  supplier.director_full_name if supplier else 'Иванов И.И.',
        'supplier_director_position': 'Директор',
        'supplier_basis':     'Устава',
        'buyer_full_name':            director.full_name if director else 'Петров П.П.',
        'buyer_director':             director.full_name if director else 'Петров П.П.',
        'buyer_director_position':    'Директор',
        'buyer_basis':                'Устава',
        'buyer_inn':                  '9876543210',
        'buyer_address':              '101000, г. Москва, ул. Тверская, д. 1',
        'buyer_accountant':           accountant.full_name if accountant else 'Бухгалтер',
        'buyer_manager':              manager.full_name if manager else 'Менеджер',
        'contract_number':    contract.id_contract,
        'contract_date':      concluded.conclusion_dates.strftime('%d.%m.%Y') if concluded and concluded.conclusion_dates else '01.01.2024',
        'contract_end_date':  concluded.payment_date.strftime('%d.%m.%Y') if concluded and concluded.payment_date else '31.12.2024',
        'place_of_contract':  'Москва',
        'consignee':          'Покупатель',
        'delivery_frequency': 'ежемесячно',
        'delivery_schedule':  'по графику',
        'transport_type':     'автомобильным транспортом',
        'payment_term':       30,
        'penalty_shortage':   0.1,
        'penalty_late_payment': 0.1,
        'renewal_term':       'один год',
        'materials':          rows,
        'total_cost':         round(total, 2),
    }


def build_arrival_context(act, delivery) -> dict:
    contract = delivery.id_contract
    rows = _contract_material_rows(contract)
    return {
        'act_number': act.id_act_of_arrival,
        'delivery_number': delivery.id_delivery,
        'contract_number': contract.id_contract,
        'date': timezone.now().strftime('%d.%m.%Y'),
        'status': act.status,
        'materials': rows,
    }


def build_divergence_context(act, delivery, divergence_items: list[dict]) -> dict:
    return {
        'act_number': act.id_act_of_arrival,
        'delivery_number': delivery.id_delivery,
        'contract_number': delivery.id_contract_id,
        'date': timezone.now().strftime('%d.%m.%Y'),
        'items': divergence_items,
    }


def generate_contract_pdf(contract: Contract) -> GeneratedPdf:
    context = build_contract_context(contract)
    return PdfDocumentService.generate_pdf(
        template_name='supply_contract_template.docx',
        context=context,
        base_name=f'contract_{contract.id_contract}',
    )


def generate_arrival_pdf(act, delivery) -> GeneratedPdf:
    context = build_arrival_context(act, delivery)
    return PdfDocumentService.generate_pdf(
        template_name='act_of_arrival_template.docx',
        context=context,
        base_name=f'act_of_arrival_{act.id_act_of_arrival}',
    )


def generate_divergence_pdf(act, delivery, divergence_items: list[dict]) -> GeneratedPdf:
    context = build_divergence_context(act, delivery, divergence_items)
    return PdfDocumentService.generate_pdf(
        template_name='act_of_divergence_template.docx',
        context=context,
        base_name=f'act_of_divergence_{act.id_act_of_arrival}',
    )

