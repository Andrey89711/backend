from django.db import migrations, models


STATUS_MAP = {
    'draft': 'created',
    'review': 'approved',
    'active': 'signed',
    'closed': 'annulled',
}


def migrate_contract_statuses_forward(apps, schema_editor):
    Contract = apps.get_model('contracts', 'Contract')
    for old, new in STATUS_MAP.items():
        Contract.objects.filter(status=old).update(status=new)


def migrate_contract_statuses_backward(apps, schema_editor):
    Contract = apps.get_model('contracts', 'Contract')
    reverse_map = {v: k for k, v in STATUS_MAP.items()}
    for old, new in reverse_map.items():
        Contract.objects.filter(status=old).update(status=new)


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0005_concluded_delivery_date_concluded_is_paid_and_more'),
    ]

    operations = [
        migrations.RunPython(
            migrate_contract_statuses_forward,
            migrate_contract_statuses_backward,
        ),
        migrations.AlterField(
            model_name='contract',
            name='status',
            field=models.CharField(
                choices=[
                    ('created', 'Создан'),
                    ('approved', 'Согласован'),
                    ('signed', 'Подписан'),
                    ('annulled', 'Аннулирован'),
                ],
                default='created',
                max_length=20,
                verbose_name='Статус',
            ),
        ),
    ]
