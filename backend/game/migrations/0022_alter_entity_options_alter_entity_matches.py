# Generated by Django 4.2 on 2023-05-12 02:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0021_alter_topic_options_alter_topicentity_position'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='entity',
            options={'ordering': ['title']},
        ),
        migrations.AlterField(
            model_name='entity',
            name='matches',
            field=models.TextField(blank=True, verbose_name='Список совпадений'),
        ),
    ]