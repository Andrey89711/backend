from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deliveries', '0003_alter_actofarrival_status_alter_delivery_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='actofarrival',
            name='acceptance_pdf_path',
            field=models.CharField(
                blank=True,
                max_length=500,
                null=True,
                verbose_name='Путь к PDF акта приемки',
            ),
        ),
        migrations.AddField(
            model_name='actofarrival',
            name='divergence_pdf_path',
            field=models.CharField(
                blank=True,
                max_length=500,
                null=True,
                verbose_name='Путь к PDF акта расхождений',
            ),
        ),
    ]
