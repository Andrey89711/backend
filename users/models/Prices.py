from django.db import models

class Prices(models.Model):
    id_prices = models.AutoField(
        primary_key=True,
        verbose_name='ID цены'
    )
    effective_dates = models.DateField(
        verbose_name='Дата начала действия'
    )
    price = models.FloatField(
        verbose_name='Цена'
    )
    id_materials = models.ForeignKey(
        'Materials',
        on_delete=models.CASCADE,
        db_column='id_materials',
        verbose_name='Материал'
    )
    id_supplier = models.ForeignKey(
        'Supplier',
        on_delete=models.CASCADE,
        db_column='id_supplier',
        verbose_name='Поставщик'
    )
    
    class Meta:
        db_table = 'prices'
        verbose_name = 'Цена'
        verbose_name_plural = 'Цены'
    
    def __str__(self):
        return f"Цена #{self.id_prices} - {self.price}"