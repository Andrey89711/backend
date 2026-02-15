from django.db import models

class Works(models.Model):
    id_storekeeper = models.ForeignKey(
        'Storekeeper',
        on_delete=models.CASCADE,
        db_column='id_storekeeper',
        verbose_name='Кладовщик'
    )
    id_warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.CASCADE,
        db_column='id_warehouse',
        verbose_name='Склад'
    )
    
    class Meta:
        db_table = 'Works'
        verbose_name = 'Работает'
        verbose_name_plural = 'Работают'
        unique_together = [['id_storekeeper', 'id_warehouse']]
    
    def __str__(self):
        return f"Кладовщик {self.id_storekeeper_id} работаеь на складе {self.id_warehouse_id}"