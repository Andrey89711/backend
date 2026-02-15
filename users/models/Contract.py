from django.db import models

class Contract(models.Model):
    id_contract = models.AutoField(
        primary_key=True,
        verbose_name='ID договора'
    )
    
    class Meta:
        db_table = 'Contract'
        verbose_name = 'Договор'
        verbose_name_plural = 'Договоры'
    
    def __str__(self):
        return f"Договор #{self.id_contract}"