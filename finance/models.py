from django.db import models


class EnterpriseBalance(models.Model):
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Баланс')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    id_director = models.ForeignKey(
        'personnel.Director', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_director', verbose_name='Директор'
    )

    class Meta:
        db_table = 'enterprise_balance'
        verbose_name = 'Баланс предприятия'
        verbose_name_plural = 'Баланс предприятия'

    def __str__(self):
        return f"Баланс: {self.amount} ₽"


class Credit(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('paid', 'Погашен'),
        ('overdue', 'Просрочен'),
    ]
    name = models.CharField(max_length=300, verbose_name='Название')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма')
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Процентная ставка')
    start_date = models.DateField(verbose_name='Дата начала')
    due_date = models.DateField(verbose_name='Дата погашения')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    creditor_name = models.CharField(max_length=300, verbose_name='Кредитор')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        db_table = 'credit'
        verbose_name = 'Кредит'
        verbose_name_plural = 'Кредиты'

    def __str__(self):
        return f"{self.name} — {self.amount} ₽ ({self.status})"


class AccountsPayable(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачена'),
        ('overdue', 'Просрочена'),
    ]
    id_supplier = models.ForeignKey(
        'partners.Supplier', on_delete=models.CASCADE,
        db_column='id_supplier', verbose_name='Поставщик'
    )
    id_concluded = models.ForeignKey(
        'contracts.Concluded', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_concluded', verbose_name='Договор'
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма')
    due_date = models.DateField(verbose_name='Дата погашения')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        db_table = 'accounts_payable'
        verbose_name = 'Кредиторская задолженность'
        verbose_name_plural = 'Кредиторская задолженность'

    def __str__(self):
        return f"Задолженность перед {self.id_supplier} — {self.amount} ₽"
