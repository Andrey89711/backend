from django.db import models

class Director(models.Model):
    id_director = models.AutoField(
        primary_key=True,
        verbose_name='ID директора'
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
        db_table = 'Director'
        verbose_name = 'Директор'
        verbose_name_plural = 'Директора'
    
    def __str__(self):
        return self.full_name