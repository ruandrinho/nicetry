# Generated by Django 4.2 on 2023-04-11 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0004_alter_topic_complexity'),
    ]

    operations = [
        migrations.AddField(
            model_name='topic',
            name='level',
            field=models.PositiveSmallIntegerField(default=3, verbose_name='Уровень'),
        ),
        migrations.AlterField(
            model_name='player',
            name='level',
            field=models.PositiveSmallIntegerField(default=3, verbose_name='Уровень'),
        ),
    ]