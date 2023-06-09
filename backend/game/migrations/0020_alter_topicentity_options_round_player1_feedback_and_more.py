# Generated by Django 4.2 on 2023-05-10 16:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0019_round_bot_answers'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='topicentity',
            options={'ordering': ['position']},
        ),
        migrations.AddField(
            model_name='round',
            name='player1_feedback',
            field=models.TextField(default='', verbose_name='Обратная связь от игрока 1'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='round',
            name='player2_feedback',
            field=models.TextField(default='', verbose_name='Обратная связь от игрока 1'),
            preserve_default=False,
        ),
    ]
