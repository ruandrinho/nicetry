# Generated by Django 4.2 on 2023-07-15 07:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0035_alter_player_telegram_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='attempt',
            field=models.PositiveSmallIntegerField(default=1, verbose_name='Попытка'),
        ),
    ]
