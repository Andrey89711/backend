from django.db import models

class Accountant(models.Model):
    id_accountant = models.AutoField(
        primary_key=True, 
        verbose_name='ID бухгалтера'
    )
    full_name = models.CharField(
        max_length=200,
        verbose_name='Полное имя'
    )
    contact_information = models.CharField(
        max_length=300,
        verbose_name='Контактная информация'
    )
    
    class Meta:
        db_table = '_Accountant'
        verbose_name = 'Бухгалтер'
        verbose_name_plural = 'Бухгалтеры'
    
    def __str__(self):
        return self.full_name