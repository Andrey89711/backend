from datetime import date

from django.utils import timezone
from rest_framework import serializers

from catalog.models import Prices
from contracts.models import Contract


class PriceResolutionError(serializers.ValidationError):
    pass


def resolve_unit_price_for_material(contract: Contract, material_id: int, unit_price: float | None = None) -> float:
    """Resolve unit price by supplier-specific active price, then latest material price fallback."""
    if unit_price is not None:
        if unit_price <= 0:
            raise PriceResolutionError({'unit_price': 'Цена за единицу должна быть больше 0.'})
        return round(float(unit_price), 2)

    today = timezone.now().date()
    supplier_id = None
    if hasattr(contract, 'concluded'):
        supplier_id = contract.concluded.id_supplier_id

    supplier_price = None
    if supplier_id:
        supplier_price = (
            Prices.objects.filter(
                id_materials_id=material_id,
                id_supplier_id=supplier_id,
                effective_dates__lte=today,
            )
            .order_by('-effective_dates', '-id_prices')
            .first()
        )
        if supplier_price is None:
            supplier_price = (
                Prices.objects.filter(
                    id_materials_id=material_id,
                    id_supplier_id=supplier_id,
                )
                .order_by('-effective_dates', '-id_prices')
                .first()
            )

    fallback_price = (
        Prices.objects.filter(id_materials_id=material_id, effective_dates__lte=today)
        .order_by('-effective_dates', '-id_prices')
        .first()
    )
    if fallback_price is None:
        fallback_price = Prices.objects.filter(id_materials_id=material_id).order_by('-effective_dates', '-id_prices').first()

    price_obj = supplier_price or fallback_price
    if price_obj is None or price_obj.price is None or float(price_obj.price) <= 0:
        raise PriceResolutionError({
            'unit_price': 'Не найдена корректная цена для материала. Укажите unit_price вручную или добавьте цену в каталог.'
        })

    return round(float(price_obj.price), 2)


def is_material_available_for_supplier(contract: Contract, material_id: int, target_date: date | None = None) -> bool:
    """
    Check whether material has at least one price row for contract supplier.
    Used to restrict material selection for supplier-bound contracts.
    """
    if target_date is None:
        target_date = timezone.now().date()

    supplier_id = None
    if hasattr(contract, 'concluded'):
        supplier_id = contract.concluded.id_supplier_id

    if not supplier_id:
        return True

    exists_now = Prices.objects.filter(
        id_materials_id=material_id,
        id_supplier_id=supplier_id,
        effective_dates__lte=target_date,
    ).exists()
    if exists_now:
        return True

    return Prices.objects.filter(
        id_materials_id=material_id,
        id_supplier_id=supplier_id,
    ).exists()

