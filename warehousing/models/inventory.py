from django.db import models

class Inventory(models.Model):
    quantity = models.FloatField(
        verbose_name='Количество'
    )
    id_warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.CASCADE,
        db_column='id_warehouse',
        verbose_name='Склад'
    )
    id_materials = models.ForeignKey(
        'catalog.Materials',
        on_delete=models.CASCADE,
        db_column='id_materials',
        verbose_name='Материал'
    )
    
    class Meta:
        db_table = 'inventory'
        verbose_name = 'Запас'
        verbose_name_plural = 'Запасы'
        unique_together = [['id_warehouse', 'id_materials']]
    
    def __str__(self):
        return f"Склад {self.id_warehouse_id} - Материал {self.id_materials_id}: {self.quantity}"
