from django.db import models

class AcceptanceOfDelivery(models.Model):
    id_storekeeper = models.ForeignKey(
        'Storekeeper',
        on_delete=models.CASCADE,
        db_column='id_storekeeper',
        verbose_name='Кладовщик'
    )
    id_act_of_arrival = models.ForeignKey(
        'ActOfArrival',
        on_delete=models.CASCADE,
        db_column='id_act_of_arrival',
        verbose_name='Акт прибытия'
    )
    
    class Meta:
        db_table = 'acceptance_of_delivery'
        verbose_name = 'Приемка поставки'
        verbose_name_plural = 'Приемки поставок'
        unique_together = [['id_storekeeper', 'id_act_of_arrival']]
    
    def __str__(self):
        return f"Кладовщик {self.id_storekeeper_id} принял поставку {self.id_act_of_arrival_id}"