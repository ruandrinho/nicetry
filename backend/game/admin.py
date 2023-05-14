from typing import Any

from django.contrib import admin
from django.http.request import HttpRequest
from django_admin_inline_paginator.admin import TabularInlinePaginated

from .models import Topic, Entity, TopicEntity, Player, Round, Answer


class TopicEntityInline(admin.TabularInline):
    model = TopicEntity
    raw_id_fields = ['topic', 'entity']
    createonly_fields = ['position', 'answers_count', 'initial_count']

    def get_extra(self, request, obj=None):
        if obj:
            return 1
        return 15

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.createonly_fields
        return []


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    inlines = [TopicEntityInline]
    list_display = ['title', 'average_score']
    search_fields = ['title']

    def save_formset(self, request: Any, form: Any, formset: Any, change: Any) -> None:
        if formset.model != TopicEntity:
            return super().save_formset(request, form, formset, change)
        instances = formset.save()
        topic = None
        if instances:
            topic = instances[0].topic
        elif formset.deleted_objects:
            topic = formset.deleted_objects[0].topic
        if not topic:
            return
        topic.gather_matches()
        topic.convert_bot_answers()
        TopicEntity.bulk_update_positions(topic=topic)


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    inlines = [TopicEntityInline]
    list_display = ['title', 'pattern']
    search_fields = ['title']

    def save_model(self, request: Any, obj: Entity, form: Any, change: Any) -> None:
        obj.compile_pattern()
        return super().save_model(request, obj, form, change)


@admin.register(TopicEntity)
class TopicEntityAdmin(admin.ModelAdmin):
    list_display = ['topic', 'entity', 'position', 'answers_count']
    raw_id_fields = ['topic', 'entity']
    search_fields = ['topic__title', 'entity__title']

    def save_model(self, request: Any, obj: TopicEntity, form: Any, change: Any) -> None:
        super().save_model(request, obj, form, change)
        obj.topic.gather_matches()
        TopicEntity.bulk_update_positions(topic=obj.topic)

    def delete_model(self, request: HttpRequest, obj: TopicEntity) -> None:
        topic = obj.topic
        super().delete_model(request, obj)
        topic.gather_matches()
        TopicEntity.bulk_update_positions(topic=topic)


class RoundInline(TabularInlinePaginated):
    model = Round
    per_page = 20
    fk_name = 'player1'
    fields = [
        'score1', 'score2', 'player1_answers', 'player2_answers', 'finished_at', 'player1_feedback', 'player2_feedback'
    ]
    readonly_fields = [
        'score1', 'score2', 'player1_answers', 'player2_answers', 'finished_at', 'player1_feedback', 'player2_feedback'
    ]
    show_change_link = False
    extra = 0


# TODO ReferralInline
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    inlines = [RoundInline]
    raw_id_fields = ['referrer']
    readonly_fields = [
        'telegram_id', 'telegram_username', 'name', 'victories', 'defeats', 'draws', 'average_score', 'level',
        'duel_victories', 'duel_defeats', 'duel_draws', 'duel_average_score', 'duel_rating', 'assigned_topics'
    ]
    search_fields = ['telegram_username', 'name']
    list_filter = ['level']


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'score1', 'score2', 'finished_at']
    list_filter = ['started_at', 'finished_at']
    readonly_fields = [
        'player1', 'player2', 'topic', 'duel', 'score1', 'score2', 'finished_at', 'bot_answers', 'player1_feedback',
        'player2_feedback'
    ]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['text', 'player', 'position', 'round', 'topic_entity']
    list_filter = [('topic_entity', admin.EmptyFieldListFilter), 'sent_at']
    raw_id_fields = ['round', 'topic_entity']
    readonly_fields = ['round', 'text', 'player', 'position']
    search_fields = ['text', 'topic_entity__topic__title', 'topic_entity__entity__title']
