# Generated by Django 4.2 on 2023-04-10 17:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0003_remove_topic_excluded_words_topic_exclusions_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='topic',
            name='complexity',
            field=models.FloatField(default=0, verbose_name='Сложность'),
        ),
    ]