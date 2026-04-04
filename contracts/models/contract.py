from django.db import models


class Contract(models.Model):
    STATUS_CREATED = 'created'
    STATUS_APPROVED = 'approved'
    STATUS_SIGNED = 'signed'
    STATUS_ANNULLED = 'annulled'

    STATUS_CHOICES = [
        (STATUS_CREATED, 'Создан'),
        (STATUS_APPROVED, 'Согласован'),
        (STATUS_SIGNED, 'Подписан'),
        (STATUS_ANNULLED, 'Аннулирован'),
    ]

    ALLOWED_TRANSITIONS = {
        STATUS_CREATED: [STATUS_APPROVED],
        STATUS_APPROVED: [STATUS_SIGNED],
        STATUS_SIGNED: [STATUS_ANNULLED],
        STATUS_ANNULLED: [],
    }

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
    waybill_file_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='Путь к накладной'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        verbose_name='Статус'
    )

    class Meta:
        db_table = 'contract'
        verbose_name = 'Договор'
        verbose_name_plural = 'Договоры'

    def __str__(self):
        return f"Договор #{self.id_contract}"

    def get_available_next_statuses(self):
        return self.ALLOWED_TRANSITIONS.get(self.status, [])

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.get_available_next_statuses()

