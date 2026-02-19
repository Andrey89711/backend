from django.db import models

class MaterialsInContract(models.Model):
    materials_quality_in_contract = models.FloatField(
        verbose_name='Качество материалов в договоре'
    )
    condition = models.CharField(
        max_length=200,
        verbose_name='Состояние/условие'
    )
    actual_quantity = models.FloatField(
        verbose_name='Фактическое количество'
    )
    id_materials = models.ForeignKey(
        'catalog.Materials',
        on_delete=models.CASCADE,
        db_column='id_materials',
        verbose_name='Материал'
    )
    id_contract = models.ForeignKey(
        'Contract',
        on_delete=models.CASCADE,
        db_column='id_contract',
        verbose_name='Договор'
    )
    
    class Meta:
        db_table = 'materials_in_contract'
        verbose_name = 'Материал в договоре'
        verbose_name_plural = 'Материалы в договоре'
        unique_together = [['id_materials', 'id_contract']]
    
    def __str__(self):
        return f"Материал {self.id_materials_id} в договоре #{self.id_contract_id}"
