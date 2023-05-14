# Generated by Django 4.2 on 2023-05-12 02:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0023_alter_topicentity_answers_count_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='topicentity',
            name='answers_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Количество ответов'),
        ),
        migrations.AlterField(
            model_name='topicentity',
            name='initial_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Изначальное количество ответов'),
        ),
        migrations.AlterField(
            model_name='topicentity',
            name='position',
            field=models.PositiveSmallIntegerField(db_index=True, default=100, verbose_name='Место'),
        ),
    ]
