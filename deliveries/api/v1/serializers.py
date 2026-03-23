from rest_framework import serializers

from deliveries.models import AcceptanceOfDelivery, ActOfArrival, Delivery
from contracts.models import Contract, MaterialsInContract


class MaterialsInContractSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='id_materials.name')
    unit = serializers.ReadOnlyField(source='id_materials.unit_of_measurement')

    class Meta:
        model = MaterialsInContract
        fields = [
            'id_materials',
            'material_name',
            'unit',
            'materials_quality_in_contract',
            'actual_quantity',
            'condition',
            'unit_price',
        ]


class DeliverySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    contract_materials = MaterialsInContractSerializer(
        source='id_contract.materialsincontract_set',
        many=True,
        read_only=True,
    )
    total_contract_value = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = '__all__'

    def get_total_contract_value(self, obj):
        materials = obj.id_contract.materialsincontract_set.all()
        return sum((m.unit_price or 0) * (m.materials_quality_in_contract or 0) for m in materials)

    def validate_id_contract(self, contract):
        if contract.status != Contract.STATUS_SIGNED:
            raise serializers.ValidationError(
                f"Поставка доступна только для договоров в статусе '{Contract.STATUS_SIGNED}'."
            )
        return contract


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


class ReceivingItemSerializer(serializers.Serializer):
    material_id = serializers.IntegerField()
    actual_quantity = serializers.FloatField(min_value=0)
    condition = serializers.CharField(required=False, allow_blank=True, default='')


class StartReceivingRequestSerializer(serializers.Serializer):
    storekeeper_id = serializers.IntegerField(required=False, allow_null=True)
    items = ReceivingItemSerializer(many=True, required=False, default=list)


class ConfirmAcceptanceRequestSerializer(serializers.Serializer):
    storekeeper_id = serializers.IntegerField()
    items = ReceivingItemSerializer(many=True, required=False, default=list)

