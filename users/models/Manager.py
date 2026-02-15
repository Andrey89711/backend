from django.db import models

class Manager(models.Model):
    id_manager = models.AutoField(
        primary_key=True,
        verbose_name='ID менеджера'
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
        db_table = 'manager'
        verbose_name = 'Менеджер'
        verbose_name_plural = 'Менеджеры'
    
    def __str__(self):
        return self.full_name