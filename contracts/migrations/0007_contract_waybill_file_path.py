from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0006_contract_status_flow'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='waybill_file_path',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='Путь к накладной'),
        ),
    ]
