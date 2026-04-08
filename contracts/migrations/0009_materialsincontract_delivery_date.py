from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0008_remove_materials_in_contract_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialsincontract',
            name='delivery_date',
            field=models.DateField(blank=True, null=True, verbose_name='Дата поставки'),
        ),
    ]
