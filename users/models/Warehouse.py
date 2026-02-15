from django.db import models

class Warehouse(models.Model):
    id_warehouse = models.AutoField(
        primary_key=True,
        verbose_name='ID склада'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название склада'
    )
    address = models.CharField(
        max_length=300,
        verbose_name='Адрес'
    )
    
    class Meta:
        db_table = 'Warehouse'
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'
    
    def __str__(self):
        return self.name