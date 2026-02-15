from django.db import models

class Materials(models.Model):
    id_materials = models.AutoField(
        primary_key=True,
        verbose_name='ID материала'
    )
    name = models.CharField(
        max_length=300,
        verbose_name='Название материала'
    )
    unit_of_measurement = models.CharField(
        max_length=30,
        verbose_name='Единица измерения'
    )
    description = models.CharField(
        max_length=500,
        verbose_name='Описание'
    )
    
    class Meta:
        db_table = 'materials'
        verbose_name = 'Материал'
        verbose_name_plural = 'Материалы'
    
    def __str__(self):
        return self.name