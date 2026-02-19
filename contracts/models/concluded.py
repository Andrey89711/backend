from django.db import models

class Concluded(models.Model):
    conclusion_dates = models.DateField(
        verbose_name='Дата заключения'
    )
    payment_date = models.DateField(
        verbose_name='Дата оплаты'
    )
    cost = models.FloatField(
        verbose_name='Стоимость'
    )
    id_supplier = models.ForeignKey(
        'partners.Supplier',
        on_delete=models.CASCADE,
        db_column='id_supplier',
        verbose_name='Поставщик'
    )
    id_contract = models.OneToOneField(
        'Contract',
        on_delete=models.CASCADE,
        db_column='id_contract',
        primary_key=True,
        verbose_name='Договор'
    )
    id_accountant = models.ForeignKey(
        'personnel.Accountant',
        on_delete=models.CASCADE,
        db_column='id_accountant',
        verbose_name='Бухгалтер'
    )
    id_manager = models.ForeignKey(
        'personnel.Manager',
        on_delete=models.CASCADE,
        db_column='id_manager',
        verbose_name='Менеджер'
    )
    id_director = models.ForeignKey(
        'personnel.Director',
        on_delete=models.CASCADE,
        db_column='id_director',
        verbose_name='Директор'
    )
    
    class Meta:
        db_table = 'concluded'
        verbose_name = 'Заключенный договор'
        verbose_name_plural = 'Заключенные договоры'
    
    def __str__(self):
        return f"Договор #{self.id_contract_id}"



