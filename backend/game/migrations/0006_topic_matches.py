# Generated by Django 4.2 on 2023-04-11 12:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0005_topic_level_alter_player_level'),
    ]

    operations = [
        migrations.AddField(
            model_name='topic',
            name='matches',
            field=models.TextField(default='{}', verbose_name='Словарь совпадений'),
        ),
    ]
