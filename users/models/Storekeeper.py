from django.db import models

class Storekeeper(models.Model):
    id_storekeeper = models.AutoField(
        primary_key=True,
        verbose_name='ID кладовщика'
    )
    full_name = models.CharField(
        max_length=180,
        verbose_name='Полное имя'
    )
    contact_information = models.CharField(
        max_length=300,
        verbose_name='Контактная информация'
    )
    
    class Meta:
        db_table = 'Storekeeper'
        verbose_name = 'Кладовщик'
        verbose_name_plural = 'Кладовщики'
    
    def __str__(self):
        return self.full_name