from django.db import models
from ..choices import DeliveryStatus

class Delivery(models.Model):
    
    id_delivery = models.AutoField(
        primary_key=True,
        verbose_name='ID поставки'
    )
    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        verbose_name='Статус'
    )
    delivery_date = models.DateField(
        verbose_name='Дата поставки'
    )
    id_contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        db_column='id_contract',
        verbose_name='Договор'
    )
    id_act_of_arrival = models.ForeignKey(
        'ActOfArrival',
        on_delete=models.CASCADE,
        db_column='id_act_of_arrival',
        verbose_name='Акт прибытия'
    )
    
    class Meta:
        db_table = 'delivery'
        verbose_name = 'Поставка'
        verbose_name_plural = 'Поставки'
    
    def __str__(self):
        return f"Поставка #{self.id_delivery} - {self.get_status_display()}"



