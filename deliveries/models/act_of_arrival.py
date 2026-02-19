from django.db import models
from ..choices import DeliveryStatus
class ActOfArrival(models.Model):
    
    id_act_of_arrival = models.AutoField(
        primary_key=True,
        verbose_name='ID акта прибытия'
    )
    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        verbose_name='Статус'
    )
    
    class Meta:
        db_table = 'act_of_arrival'
        verbose_name = 'Акт прибытия'
        verbose_name_plural = 'Акты прибытия'
    
    def __str__(self):
        return f"Акт прибытия #{self.id_act_of_arrival} - {self.get_status_display()}"
