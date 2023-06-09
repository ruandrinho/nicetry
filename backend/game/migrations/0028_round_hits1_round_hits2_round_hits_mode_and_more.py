# Generated by Django 4.2 on 2023-06-05 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0027_alter_topicentity_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='hits1',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Хиты 1'),
        ),
        migrations.AddField(
            model_name='round',
            name='hits2',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Хиты 2'),
        ),
        migrations.AddField(
            model_name='round',
            name='hits_mode',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Дуэль'),
        ),
        migrations.AddField(
            model_name='topic',
            name='average_score_hits_mode',
            field=models.FloatField(default=0, verbose_name='Средний результат в режиме хитов'),
        ),
        migrations.AlterField(
            model_name='round',
            name='bot_answers',
            field=models.TextField(default='{}', verbose_name='Возможные ответы бота'),
        ),
        migrations.AlterField(
            model_name='round',
            name='player1_feedback',
            field=models.TextField(verbose_name='Обратная связь 1'),
        ),
        migrations.AlterField(
            model_name='round',
            name='player2_feedback',
            field=models.TextField(verbose_name='Обратная связь 2'),
        ),
        migrations.AlterField(
            model_name='round',
            name='score1',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Очки 1'),
        ),
        migrations.AlterField(
            model_name='round',
            name='score2',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Очки 2'),
        ),
    ]
