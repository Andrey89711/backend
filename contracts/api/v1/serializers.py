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
    """
    Основной сериализатор для заключенных договоров.
    Включает информацию о контрагентах и сотрудниках.
    """
    # Читаемые поля для отображения имен связанных объектов
    supplier_name = serializers.ReadOnlyField(source='id_supplier.name')
    accountant_name = serializers.ReadOnlyField(source='id_accountant.full_name')
    manager_name = serializers.ReadOnlyField(source='id_manager.full_name')
    director_name = serializers.ReadOnlyField(source='id_director.full_name')
    
    # Вложенный список материалов
    materials = MaterialsInContractSerializer(
        source='id_contract.materialsincontract_set', 
        many=True, 
        read_only=True
    )

    # Пример вычисляемого поля (если нужно дублировать или форматировать стоимость)
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
        read_only_fields = ['id_contract'] # ID создается через связь с Contract

    def get_cost_formatted(self, obj):
        return f"{obj.cost:,.2f} ₽"

class ContractSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для модели Contract (если нужно управлять просто ID)"""
    concluded_info = ConcludedSerializer(source='concluded', read_only=True)
    
    class Meta:
        model = Contract
        fields = ['id_contract', 'concluded_info']