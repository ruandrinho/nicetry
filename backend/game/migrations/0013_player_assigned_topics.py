# Generated by Django 4.2 on 2023-04-14 08:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0012_remove_topic_updated'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='assigned_topics',
            field=models.CharField(default='', max_length=20, verbose_name='Список назначенных тем'),
            preserve_default=False,
        ),
    ]
