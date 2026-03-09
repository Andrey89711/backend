from rest_framework import serializers
from ...models import Concluded, Contract, MaterialsInContract


class MaterialsInContractSerializer(serializers.ModelSerializer):
    """Сериализатор для материалов внутри договора"""
    material_name = serializers.ReadOnlyField(source='id_materials.name')
    unit = serializers.ReadOnlyField(source='id_materials.unit_of_measurement')

    class Meta:
        model = MaterialsInContract
        fields = [
            'id_materials', 'material_name', 'unit', 
            'materials_quality_in_contract', 'actual_quantity', 'condition'
        ]

class ConcludedSerializer(serializers.ModelSerializer):
    """Основной сериализатор для заключенных договоров."""
    supplier_name = serializers.ReadOnlyField(source='id_supplier.name')
    accountant_name = serializers.ReadOnlyField(source='id_accountant.full_name')
    manager_name = serializers.ReadOnlyField(source='id_manager.full_name')
    director_name = serializers.ReadOnlyField(source='id_director.full_name')
    
    materials = MaterialsInContractSerializer(
        source='id_contract.materialsincontract_set', 
        many=True, 
        read_only=True
    )

    cost_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Concluded
        fields = [
            'id_contract', 'conclusion_dates', 'payment_date', 'cost', 'cost_formatted',
            'id_supplier', 'supplier_name',
            'id_accountant', 'accountant_name',
            'id_manager', 'manager_name',
            'id_director', 'director_name',
            'materials'
        ]
        read_only_fields = ['id_contract']

    def get_cost_formatted(self, obj):
        return f"{obj.cost:,.2f} ₽"

class ContractSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для модели Contract"""
    concluded_info = ConcludedSerializer(source='concluded', read_only=True)
    
    filename = serializers.SerializerMethodField()
    file_download_url = serializers.SerializerMethodField()
    file_preview_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Contract
        fields = [
            'id_contract',
            'status',
            'created_at',
            'file_path',
            'filename',
            'file_download_url',
            'file_preview_url',
            'concluded_info'
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
        if request:
            return request.build_absolute_uri(f'/api/contracts/{obj.id_contract}/file/download/')
        return f'/api/contracts/{obj.id_contract}/file/download/'
    
    def get_file_preview_url(self, obj):
        if not obj.file_path:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/contracts/{obj.id_contract}/file/download/?inline=true')
        return f'/api/contracts/{obj.id_contract}/file/download/?inline=true'