# Generated by Django 4.2 on 2023-04-16 03:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0013_player_assigned_topics'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='referrer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='game.player', verbose_name='Реферер'),
        ),
        migrations.AlterField(
            model_name='answer',
            name='round',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='answers', to='game.round', verbose_name='Раунд'),
        ),
        migrations.AlterField(
            model_name='round',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rounds', to='game.player', verbose_name='Игрок'),
        ),
        migrations.AlterField(
            model_name='round',
            name='topic',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rounds', to='game.topic', verbose_name='Тема'),
        ),
        migrations.AlterField(
            model_name='topicentity',
            name='entity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.entity', verbose_name='Сущность'),
        ),
        migrations.AlterField(
            model_name='topicentity',
            name='topic',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.topic', verbose_name='Тема'),
        ),
    ]