from django.db import models

class Contract(models.Model):
    id_contract = models.AutoField(
        primary_key=True,
        verbose_name='ID договора'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    file_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='Путь к файлу'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Черновик'),
            ('review', 'На согласовании'),
            ('active', 'Активен'),
            ('closed', 'Закрыт'),
        ],
        default='draft',
        verbose_name='Статус'
    )

    class Meta:
        db_table = 'contract'
        verbose_name = 'Договор'
        verbose_name_plural = 'Договоры'
    
    def __str__(self):
        return f"Договор #{self.id_contract}"