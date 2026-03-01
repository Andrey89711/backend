from rest_framework import serializers
from deliveries.models import AcceptanceOfDelivery, ActOfArrival, Delivery
from contracts.models import MaterialsInContract # Проверьте путь к приложению контрактов

class MaterialsInContractSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='id_materials.name')
    unit = serializers.ReadOnlyField(source='id_materials.unit_of_measurement')

    class Meta:
        model = MaterialsInContract
        fields = ['id_materials', 'material_name', 'unit', 'materials_quality_in_contract', 'actual_quantity', 'condition']

class DeliverySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # Выводим состав материалов договора, к которому привязана поставка
    contract_materials = MaterialsInContractSerializer(
        source='id_contract.materialsincontract_set', 
        many=True, 
        read_only=True
    )
    # Расчетное поле: общая сумма по договору (пример бизнес-логики)
    total_contract_value = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = '__all__'

    def get_total_contract_value(self, obj):
        # Здесь можно добавить логику умножения кол-ва на цену, если нужно
        materials = obj.id_contract.materialsincontract_set.all()
        return sum(m.actual_quantity for m in materials) # Пока просто сумма количеств

class ActOfArrivalSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ActOfArrival
        fields = '__all__'

class AcceptanceOfDeliverySerializer(serializers.ModelSerializer):
    storekeeper_name = serializers.ReadOnlyField(source='id_storekeeper.full_name')
    act_id = serializers.ReadOnlyField(source='id_act_of_arrival.id_act_of_arrival')

    class Meta:
        model = AcceptanceOfDelivery
        fields = '__all__'
