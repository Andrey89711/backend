from django.db import models

class Supplier(models.Model):
    id_supplier = models.AutoField(
        primary_key=True,
        verbose_name='ID поставщика'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название компании'
    )
    tax_id = models.CharField(
        max_length=200,
        verbose_name='ИНН/Налоговый номер'
    )
    accounted_full_name = models.CharField(
        max_length=200,
        verbose_name='ФИО бухгалтера'
    )
    director_full_name = models.CharField(
        max_length=200,
        verbose_name='ФИО директора'
    )
    payment_details = models.CharField(
        max_length=500,
        verbose_name='Платежные реквизиты'
    )
    
    class Meta:
        db_table = 'supplier'
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
    
    def __str__(self):
        return self.name