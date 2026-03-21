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
        ]
        read_only_fields = ['materials', 'computed_cost', 'cost_formatted']

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

    class Meta:
        model = Contract
        fields = [
            'id_contract', 'status', 'created_at', 'file_path',
            'filename', 'file_download_url', 'file_preview_url', 'concluded_info'
        ]
        read_only_fields = ['id_contract', 'created_at', 'filename', 'file_download_url', 'file_preview_url']

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
