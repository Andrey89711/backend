from rest_framework import serializers
from ...models import Concluded, Contract, MaterialsInContract


class MaterialsInContractSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='id_materials.name')
    unit = serializers.ReadOnlyField(source='id_materials.unit_of_measurement')

    class Meta:
        model = MaterialsInContract
        fields = [
            'id', 'id_materials', 'material_name', 'unit', 'id_contract',
            'materials_quality_in_contract', 'unit_price',
            'actual_quantity', 'condition',
        ]

    def validate_unit_price(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('Цена за единицу должна быть больше 0.')
        return value


class ConcludedSerializer(serializers.ModelSerializer):
    supplier_name = serializers.ReadOnlyField(source='id_supplier.name')
    accountant_name = serializers.ReadOnlyField(source='id_accountant.full_name')
    manager_name = serializers.ReadOnlyField(source='id_manager.full_name')
    director_name = serializers.ReadOnlyField(source='id_director.full_name')
    computed_cost = serializers.SerializerMethodField()
    cost_formatted = serializers.SerializerMethodField()
    materials = MaterialsInContractSerializer(
        source='id_contract.materialsincontract_set',
        many=True, read_only=True
    )
    status = serializers.CharField(source='id_contract.status', read_only=True)
    available_next_statuses = serializers.SerializerMethodField()

    class Meta:
        model = Concluded
        fields = [
            'id_contract', 'conclusion_dates', 'payment_date', 'delivery_date',
            'cost', 'computed_cost', 'cost_formatted', 'is_paid',
            'id_supplier', 'supplier_name',
            'id_accountant', 'accountant_name',
            'id_manager', 'manager_name',
            'id_director', 'director_name',
            'materials',
            'status',
            'available_next_statuses'
        ]
        read_only_fields = ['materials', 'computed_cost', 'cost_formatted', 'status', 'available_next_statuses']

    def get_available_next_statuses(self, obj):
        return obj.id_contract.get_available_next_statuses()

    def get_computed_cost(self, obj):
        total = sum(
            (m.unit_price or 0) * (m.materials_quality_in_contract or 0)
            for m in obj.id_contract.materialsincontract_set.all()
        )
        return round(total, 2)

    def get_cost_formatted(self, obj):
        return f"{obj.cost:,.2f} ₽"


class ContractSerializer(serializers.ModelSerializer):
    concluded_info = ConcludedSerializer(source='concluded', read_only=True)
    filename = serializers.SerializerMethodField()
    file_download_url = serializers.SerializerMethodField()
    file_preview_url = serializers.SerializerMethodField()
    available_next_statuses = serializers.SerializerMethodField()
    document_type = serializers.SerializerMethodField()
    divergence_pdf_url = serializers.SerializerMethodField()
    act_id = serializers.SerializerMethodField()
    act_pdf_url = serializers.SerializerMethodField()
    waybill_pdf_url = serializers.SerializerMethodField()
    waybill_id = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            'id_contract', 'status', 'created_at', 'file_path',
            'filename', 'file_download_url', 'file_preview_url',
            'available_next_statuses', 'concluded_info',
            'document_type', 'divergence_pdf_url', 'act_id', 'act_pdf_url',
            'waybill_pdf_url', 'waybill_id',
        ]
        read_only_fields = [
            'id_contract', 'created_at', 'filename',
            'file_download_url', 'file_preview_url', 'available_next_statuses',
            'document_type', 'divergence_pdf_url', 'act_id', 'act_pdf_url',
            'waybill_pdf_url', 'waybill_id',
        ]

    def _get_act(self, obj):
        delivery = obj.delivery_set.select_related('id_act_of_arrival').first()
        if delivery and delivery.id_act_of_arrival:
            return delivery.id_act_of_arrival
        return None

    def get_filename(self, obj):
        if not obj.file_path:
            return None
        from pathlib import Path
        return Path(obj.file_path).name

    def get_file_download_url(self, obj):
        if not obj.file_path:
            return None
        request = self.context.get('request')
        url = f'/api/contracts/{obj.id_contract}/file/download/'
        return request.build_absolute_uri(url) if request else url

    def get_file_preview_url(self, obj):
        if not obj.file_path:
            return None
        request = self.context.get('request')
        url = f'/api/contracts/{obj.id_contract}/file/download/?inline=true'
        return request.build_absolute_uri(url) if request else url

    def get_available_next_statuses(self, obj):
        return obj.get_available_next_statuses()

    def get_act_id(self, obj):
        try:
            act = self._get_act(obj)
            return act.id_act_of_arrival if act else None
        except Exception:
            return None

    def get_document_type(self, obj):
        return 'supply_contract'

    def get_act_pdf_url(self, obj):
        try:
            act = self._get_act(obj)
            if act and act.acceptance_pdf_path:
                from django.conf import settings
                media_url = settings.MEDIA_URL.rstrip('/')
                path = act.acceptance_pdf_path.lstrip('/')
                url = f'{media_url}/{path}'
                request = self.context.get('request')
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None

    def get_divergence_pdf_url(self, obj):
        try:
            act = self._get_act(obj)
            if act and act.divergence_pdf_path:
                from django.conf import settings
                media_url = settings.MEDIA_URL.rstrip('/')
                path = act.divergence_pdf_path.lstrip('/')
                url = f'{media_url}/{path}'
                request = self.context.get('request')
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None

    def get_waybill_id(self, obj):
        return obj.id_contract if obj.waybill_file_path else None

    def get_waybill_pdf_url(self, obj):
        if not obj.waybill_file_path:
            return None
        from django.conf import settings
        media_url = settings.MEDIA_URL.rstrip('/')
        path = obj.waybill_file_path.lstrip('/')
        url = f'{media_url}/{path}'
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url


class SetContractStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[status for status, _ in Contract.STATUS_CHOICES])

class ActOfDivergenceItemSerializer(serializers.Serializer):
    name       = serializers.CharField()
    series     = serializers.CharField(default='', allow_blank=True)
    unit       = serializers.CharField(default='шт')
    price      = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    qty_doc    = serializers.DecimalField(max_digits=12, decimal_places=3, default=0)
    sum_doc    = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)
    qty_actual = serializers.DecimalField(max_digits=12, decimal_places=3, default=0)
    sum_actual = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)


class ActOfDivergenceSerializer(serializers.Serializer):
    organization_name    = serializers.CharField()
    organization_address = serializers.CharField()
    act_date  = serializers.DateField()
    act_place = serializers.CharField()
    reception_start_hour = serializers.CharField()
    reception_start_min  = serializers.CharField(default='00', allow_blank=True)
    reception_end_hour   = serializers.CharField()
    reception_end_min    = serializers.CharField(default='00', allow_blank=True)
    commission_members   = serializers.CharField()
    commission_signature = serializers.CharField(default='', allow_blank=True)
    representative_name  = serializers.CharField()
    certificate_number   = serializers.CharField(default='', allow_blank=True)
    certificate_date     = serializers.DateField(required=False, allow_null=True)
    sender_name  = serializers.CharField()
    carrier_name = serializers.CharField(default='', allow_blank=True)
    contract_number = serializers.CharField()
    contract_date   = serializers.DateField()
    invoice_number  = serializers.CharField()
    invoice_date    = serializers.DateField()
    sign_date = serializers.DateField(required=False, allow_null=True)
    sign_name = serializers.CharField(default='', allow_blank=True)
    items = ActOfDivergenceItemSerializer(many=True)

    def to_docx_context(self) -> dict:
        d = self.validated_data

        def fmt_date(value):
            if not value:
                return '___'
            from datetime import date
            if isinstance(value, date):
                return value.strftime('%d.%m.%Y')
            return str(value)

        items = [
            {
                'name':       item['name'],
                'series':     item.get('series', ''),
                'unit':       item.get('unit', 'шт'),
                'price':      str(item.get('price', '')),
                'qty_doc':    str(item.get('qty_doc', '')),
                'sum_doc':    str(item.get('sum_doc', '')),
                'qty_actual': str(item.get('qty_actual', '')),
                'sum_actual': str(item.get('sum_actual', '')),
            }
            for item in d['items']
        ]

        return {
            'organization_name':    d['organization_name'],
            'organization_address': d['organization_address'],
            'act_date':             fmt_date(d['act_date']),
            'act_place':            d['act_place'],
            'reception_start_hour': d['reception_start_hour'],
            'reception_start_min':  d.get('reception_start_min', '00'),
            'reception_end_hour':   d['reception_end_hour'],
            'reception_end_min':    d.get('reception_end_min', '00'),
            'commission_members':   d['commission_members'],
            'commission_signature': d.get('commission_signature', ''),
            'representative_name':  d['representative_name'],
            'certificate_number':   d.get('certificate_number', ''),
            'certificate_date':     fmt_date(d.get('certificate_date')),
            'sender_name':          d['sender_name'],
            'carrier_name':         d.get('carrier_name', ''),
            'contract_number':      d['contract_number'],
            'contract_date':        fmt_date(d['contract_date']),
            'invoice_number':       d['invoice_number'],
            'invoice_date':         fmt_date(d['invoice_date']),
            'sign_date':            fmt_date(d.get('sign_date')),
            'sign_name':            d.get('sign_name', ''),
            'items':                items,
        }
