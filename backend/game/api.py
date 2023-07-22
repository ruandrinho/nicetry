from typing import Optional

from django.shortcuts import get_object_or_404
from ninja import Router, Field, Schema
from .models import Topic, Entity, TopicEntity, Player, Round, Answer, Config

router = Router()


class Message200(Schema):
    detail: str


class Message403(Schema):
    detail: str


class Message404(Schema):
    detail: str


class TopicSchema(Schema):
    id: int
    title: str


@router.get('/topic', response={200: TopicSchema, 404: Message404})
def get_topic(request, topic_id: int):
    topic = Topic.find(topic_id=topic_id)
    return topic


@router.get('/random-topics', response={200: list[TopicSchema], 403: Message403})
def get_random_topics(request, player1_id: int = 0, player2_id: int = 0):
    player1 = Player.find_or_create(player_id=player1_id)
    if not player2_id:
        if player1.assigned_topics:
            return list(Topic.objects.assigned_to(player1))
        topics = Topic.objects.exclude_played_by(player1)
        if not topics:
            return 403, {'detail': 'Не осталось доступных тем для данного игрока'}
        random_topics = topics.for_level(player1.level).random(Config.topics_count)
        if random_topics.count() < Config.topics_count:
            random_topics = topics.random(Config.topics_count)
        player1.assign_topics(random_topics)
        return list(random_topics)
    player2 = Player.find_or_create(player_id=player2_id)
    topics = Topic.objects.exclude_played_by(player1).exclude_played_by(player2)
    if not topics:
        return 403, {'detail': 'Не осталось доступных тем для данной пары игроков'}
    random_topics = topics.for_level(player1.level).for_level(player2.level).random(Config.topics_count)
    if random_topics.count() < Config.topics_count:
        random_topics = topics.random(Config.topics_count)
    return list(random_topics)


class EntitySchema(Schema):
    id: int
    title: str
    pattern: str


@router.get('/entities', response={200: list[EntitySchema]})
def search_entities(request, term: str):
    return Entity.objects.filter(title__icontains=term)


class PlayerInSchema(Schema):
    telegram_id: int = 1
    telegram_username: Optional[str] = None
    name: Optional[str] = None


class PlayerOutSchema(Schema):
    id: int
    telegram_id: int
    displayed_name: str
    name_with_id: str
    rating: int = 0
    position: int = None


@router.get('/players', response={200: list[PlayerOutSchema]})
def get_players(request, group: Optional[str] = None):
    if group == 'INACTIVE':
        return Player.objects.inactive()
    return Player.objects.all()


# TODO duel rating
@router.get('/rating', response={200: list[PlayerOutSchema]})
def get_rating(request):
    return Player.objects.top(10)


@router.post('/player', response={200: PlayerOutSchema})
def find_player(request, data: PlayerInSchema):
    if not data.telegram_username:
        data.telegram_username = ''
    if not data.name:
        data.name = ''
    player = Player.find_or_create(
        telegram_id=data.telegram_id,
        telegram_username=data.telegram_username,
        name=data.name
    )
    return player


class ReferrerSchema(Schema):
    player_id: int
    referrer_id: int


@router.put('/player', response={200: Message200, 404: Message404})
def put_player(request, data: ReferrerSchema):
    player = Player.find_or_create(player_id=data.player_id)
    if not player.referrer:
        player.referrer = Player.find_or_create(player_id=data.referrer_id)
        player.save()
    return {'detail': 'ok'}


class RoundInSchema(Schema):
    player1_id: int
    player2_id: int
    topic_id: int
    hits_mode: bool = False


class RoundOutSchema(Schema):
    id: int
    attempt: int = 0


@router.post('/round', response={200: RoundOutSchema, 403: Message403, 404: Message404})
def start_round(request, data: RoundInSchema):
    player1 = Player.find_or_create(player_id=data.player1_id)
    if not data.player2_id:
        player1.clear_assigned_topics()
        round, created = Round.objects.get_or_create(player1=player1, topic_id=data.topic_id, hits_mode=data.hits_mode)
        if created:
            round.update_bot_answers()
            return {'id': round.id}
        return 403, {'detail': 'Тема уже сыграна'}
    player2 = Player.find_or_create(player_id=data.player2_id)
    round, created = Round.objects.get_or_create(
        player1=player1,
        player2=player2,
        topic_id=data.topic_id,
        hits_mode=data.hits_mode,
        duel=True
    )
    if created:
        return {'id': round.id}
    return 403, {'detail': 'Тема уже сыграна'}


class FeedbackSchema(Schema):
    round_id: int
    feedback: str
    player: int = 1


@router.put('/round', response={200: Message200, 404: Message404})
def feedback(request, data: FeedbackSchema):
    round = get_object_or_404(Round, id=data.round_id)
    round.add_feedback(data.feedback, data.player)
    return {'detail': 'ok'}


class FinishSchema(Schema):
    round_id: int
    score1: int = 0
    score2: int = 0
    hits1: int = 0
    hits2: int = 0
    abort_side: int = 0


class ResultSchema(Schema):
    rating1: int = 0
    position1: int = 0
    rating2: int = 0
    position2: int = 0


@router.post('/finish', response={200: ResultSchema, 404: Message404})
def finish_round(request, data: FinishSchema):
    round = get_object_or_404(Round, id=data.round_id)
    rating1, position1, rating2, position2 = round.finish(
        score1=data.score1,
        score2=data.score2,
        hits1=data.hits1,
        hits2=data.hits2,
        abort_side=data.abort_side
    )
    return {'rating1': rating1, 'position1': position1, 'rating2': rating2, 'position2': position2}


class ObjectGroupModerationSchema(Schema):
    ids: list[int]


@router.post('check-rounds', response={200: Message200})
def check_rounds(request, data: ObjectGroupModerationSchema):
    Round.set_checked(data.ids)
    return {'detail': 'ok'}


class AnswerSchema(Schema):
    round_id: int
    answer: str
    entity_id: int = None
    side: int = 1


class TopicEntitySchema(Schema):
    id: int
    title: str = Field(..., alias='entity.title')
    position: int
    points: int
    # share: float


class ChatgptAnswerSchema(Schema):
    text: str
    entity: TopicEntitySchema = None


class AttemptSchema(Schema):
    attempt: int = 0
    entities: list[TopicEntitySchema] = None
    skipped: bool = False
    chatgpt_answer: ChatgptAnswerSchema = None


@router.post('/answer', response={200: AttemptSchema, 403: Message403, 404: Message404})
def answer(request, data: AnswerSchema):
    round = get_object_or_404(Round, id=data.round_id)

    skipped = data.answer == '-'

    if data.entity_id:
        topic_entity = get_object_or_404(TopicEntity, id=data.entity_id)
        created = Answer.get_or_create(round=round, topic_entity=topic_entity, text=data.answer, player=data.side)
        if not created:
            round.add_declined_answer(data.answer, 'CHOICE REPEAT')
            return 403, {'detail': 'Этот ответ засчитан, введите другой'}
        if not round.duel:
            chatgpt_answer, chatgpt_answer_entity = round.get_bot_answer()
            return {
                'attempt': round.attempt,
                'entities': [topic_entity],
                'chatgpt_answer': {
                    'text': chatgpt_answer,
                    'entity': chatgpt_answer_entity
                }
            }
        return {
            'attempt': round.attempt,
            'entities': [topic_entity]
        }

    topic_entities = round.topic.get_matching_entities(data.answer) if not skipped else None
    if not topic_entities:
        if not skipped:
            created = Answer.get_or_create(round=round, text=data.answer, player=data.side)
            if not created:
                round.add_declined_answer(data.answer, 'NEW REPEAT')
                return 403, {'detail': 'Этот ответ засчитан, введите другой'}
        if not round.duel:
            chatgpt_answer, chatgpt_answer_entity = round.get_bot_answer()
            return {
                'attempt': round.attempt,
                'skipped': skipped,
                'chatgpt_answer': {
                    'text': chatgpt_answer,
                    'entity': chatgpt_answer_entity
                }
            }
        return {
            'attempt': round.attempt,
            'skipped': skipped
        }
    elif len(topic_entities) == 1:
        created = Answer.get_or_create(round=round, topic_entity=topic_entities[0], text=data.answer, player=data.side)
        if not created:
            round.add_declined_answer(data.answer, topic_entities[0].entity.title)
            return 403, {'detail': 'Этот ответ засчитан, введите другой'}
        if not round.duel:
            chatgpt_answer, chatgpt_answer_entity = round.get_bot_answer()
            return {
                'attempt': round.attempt,
                'entities': topic_entities,
                'chatgpt_answer': {
                    'text': chatgpt_answer,
                    'entity': chatgpt_answer_entity
                }
            }
        return {
            'attempt': round.attempt,
            'entities': topic_entities
        }

    return {
        'attempt': round.attempt,
        'entities': topic_entities
    }


class AnswerModerationSchema(Schema):
    answer_id: int
    topic_entity_id: int | None = None
    entity_id: int | None = None
    entity_title: str | None = None
    entity_pattern: str | None = None


@router.put('/answer', response={200: Message200, 404: Message404})
def put_answer(request, data: AnswerModerationSchema):
    answer = get_object_or_404(Answer, id=data.answer_id)
    if data.topic_entity_id:
        topic_entity = get_object_or_404(TopicEntity, id=data.topic_entity_id)
        answer.assign_topic_entity(topic_entity=topic_entity)
        topic_entity.entity.update_title_and_pattern(data.entity_title, data.entity_pattern)
    elif data.entity_id:
        entity = get_object_or_404(Entity, id=data.entity_id)
        entity.update_title_and_pattern(data.entity_title, data.entity_pattern)
        topic_entity = TopicEntity.objects.create(topic=answer.round.topic, entity=entity)
        answer.assign_topic_entity(topic_entity=topic_entity)
    elif data.entity_title and data.entity_pattern:
        # TODO strange creation
        entity, created = Entity.objects.get_or_create(
            title=data.entity_title,
            defaults={'pattern': data.entity_pattern}
        )
        if created:
            entity.compile_pattern()
        elif entity.pattern != data.entity_pattern:
            entity.compile_pattern(data.entity_pattern)
        topic_entity = TopicEntity.objects.create(topic=answer.round.topic, entity=entity)
        answer.assign_topic_entity(topic_entity=topic_entity)
    answer.round.topic.gather_matches()
    return {'detail': 'ok'}


@router.post('discard-answers', response={200: Message200})
def discard_answers(request, data: ObjectGroupModerationSchema):
    Answer.discard(data.ids)
    return {'detail': 'ok'}
