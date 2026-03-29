from django.db import models


class Admin(models.Model):
    id_admin = models.AutoField(primary_key=True, verbose_name='ID администратора')
    full_name = models.CharField(max_length=200, verbose_name='Полное имя')
    contact_information = models.CharField(max_length=300, verbose_name='Контактная информация')

    class Meta:
        db_table = 'admin'
        verbose_name = 'Администратор'
        verbose_name_plural = 'Администраторы'

    def __str__(self):
        return self.full_name
