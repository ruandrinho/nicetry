import itertools
import json
import re
from collections import defaultdict
from typing import Optional

from django.contrib import admin
from django.db import models
from django.db.models import Avg, F
from django.http import Http404
from django.utils import timezone
import jellyfish


class Config:
    topics_count: int = 3
    attempts_count: int = 5
    points: tuple[int] = (10, 9, 8, 7, 6, 5, 4, 3, 2, 1)
    initial_rounds: int = 11
    topic_levels: tuple[int] = (0, 6, 12, 18, 24, 40)


def remove_successive_letters(s: str) -> str:
    result = []
    for char, group in itertools.groupby(s):
        if char.isdigit() or char in 'ix+':
            result.extend(list(group))
        else:
            result.append(char)
    return ''.join(result)


def simplify_text(text: str, odd_words: list[str] = [], extra_allowed_symbols: str = '') -> str:
    text = text.lower().replace('э', 'е').replace('ё', 'е').replace('й', 'и')
    text = ''.join(char for char in text if char.isalnum() or char in extra_allowed_symbols)
    text = remove_successive_letters(text)
    for word in odd_words:
        text = text.replace(word, '')
    return text


class TopicQuerySet(models.QuerySet):

    def assigned_to(self, player: 'Player'):
        return self.filter(id__in=player.assigned_topics.split())

    def exclude_played_by(self, player: 'Player'):
        return self.exclude(
            id__in=Round.objects.filter(player1=player).values_list('topic_id')
        )

    def for_level(self, level: int):
        ranges = len(Config.topic_levels) - 1
        min_topic_level = max(1, level - 2)
        max_topic_level = min(ranges, level + 2)
        min_average_score = Config.topic_levels[ranges - max_topic_level]
        max_average_score = Config.topic_levels[ranges + 1 - min_topic_level]
        return self.filter(
            average_score__gte=min_average_score,
            average_score__lte=max_average_score
        )

    def random(self, count: int):
        return self.order_by('?')[:count]


class Topic(models.Model):
    title = models.CharField('Название', max_length=100, unique=True)
    hint = models.TextField('Подсказка', blank=True)
    matches = models.TextField('Словарь совпадений', default='{}')
    exclusions = models.CharField('Исключаемые слова', max_length=100, blank=True)
    average_score = models.FloatField('Средний результат', default=0)
    bot_answers = models.TextField('Список ответов бота', default='{}')

    objects = TopicQuerySet.as_manager()

    class Meta:
        ordering = ['title']

    def __str__(self) -> str:
        return self.title

    @classmethod
    def find(cls, id: int = 0, title: str = '') -> Optional['Topic']:
        try:
            if id:
                topic = cls.objects.get(id=id)
            else:
                topic = cls.objects.get(title=title)
        except cls.DoesNotExist:
            raise Http404('Тема не найдена')
        return topic

    def convert_bot_answers(self) -> None:
        if self.bot_answers.startswith('{'):
            return
        new_bot_answers = {}
        for answer in self.bot_answers.split(', '):
            topic_entity = self.get_matching_entities(answer)[0]
            new_bot_answers[topic_entity.id] = answer
        self.bot_answers = json.dumps(new_bot_answers, ensure_ascii=False)
        self.save()

    def gather_matches(self) -> None:
        matches = defaultdict(list)
        odd_words = self.exclusions.split()
        for entity in self.entities.all():
            for match in entity.matches.split():
                for word in odd_words:
                    match = match.replace(word, '')
                matches[match].append(entity.id)
        self.matches = json.dumps(matches, ensure_ascii=False)
        self.save()

    def get_matching_entities(self, text: str) -> Optional[list['TopicEntity']]:
        extra_allowed_symbols = ''
        if self.title == 'Языки программирования':
            extra_allowed_symbols = '+#'
        text = simplify_text(text, odd_words=self.exclusions.split(), extra_allowed_symbols=extra_allowed_symbols)
        matches = json.loads(self.matches)
        if text in matches:
            return list(TopicEntity.objects.filter(entity__id__in=matches[text], topic=self))
        for match in matches:
            if jellyfish.damerau_levenshtein_distance(match, text) <= 1:
                return list(TopicEntity.objects.filter(entity__id__in=matches[match], topic=self))
        return None

    def update_statistics(self) -> None:
        self.average_score = self.rounds.finished().aggregate(avg=Avg('score1'))['avg']
        self.save()
        TopicEntity.bulk_update_positions(topic=self)


class Entity(models.Model):
    title = models.CharField('Название', max_length=100, unique=True)
    pattern = models.CharField('Паттерн', max_length=100)
    matches = models.TextField('Список совпадений', blank=True)
    topics = models.ManyToManyField(Topic, through='TopicEntity', related_name='entities')

    class Meta:
        ordering = ['title']
        verbose_name_plural = 'entities'

    def __str__(self) -> str:
        return self.title

    def compile_pattern(self) -> None:
        matches: list[str] = []

        # Replace spaces into '|' inside bracket groups
        pattern: str = re.sub(
            r'\(([^)]*)\)',
            lambda match: f'({match.group(1).replace(" ", "|")})',
            self.pattern
        )

        if ' = ' in pattern:
            pattern, obligatory_combinations = pattern.split(' = ')
            obligatory_combinations: list[tuple[int, ...]] = [
                tuple(int(num) - 1 for num in combination) for combination in obligatory_combinations.split()
            ]

        def permutate(list_: list[str]) -> list[str]:
            if not list_:
                return ['']
            head, *tail = list_
            tail_expanded = permutate(tail)
            if isinstance(head, list):
                return [item + tail_item for item in head for tail_item in tail_expanded]
            else:
                return [head + tail_item for tail_item in tail_expanded]

        def parse_bracket_group(item: str) -> list[str]:
            if len(item) == 1:
                return [item, '']
            elif '|' in item:
                return item.split('|')
            return list(item)

        def parse_ordinal(item: str) -> list[str]:
            num = int(item[:-1])
            if num > 30:
                return [item]
            male: bool = item[-1] == 'и'
            male_ordinals = [
                'нулевой', 'первыи', 'второи', 'трети', 'четвертыи', 'пятыи', 'шестои', 'седьмои', 'восьмои', 'девятыи',
                'десятыи', 'одинадцатыи', 'двенадцатыи', 'тринадцатыи', 'четырнадцатыи', 'пятнадцатыи', 'шестнадцатыи',
                'семнадцатыи', 'восемнадцатыи', 'девятнадцатыи', 'двадцатыи', 'двадцатьпервыи', 'двадцатьвторои',
                'двадцатьтрети', 'двадцатьчетвертыи', 'двадцатьпятыи', 'двадцатьшестои', 'двадцатьседьмои',
                'двадцатьвосьмои', 'двадцатьдевятыи', 'тридцатыи'
            ]
            female_ordinals = [
                'нулевая', 'первая', 'вторая', 'третья', 'четвертая', 'пятая', 'шестая', 'седьмая', 'восьмая',
                'девятая', 'десятая', 'одинадцатая', 'двенадцатая', 'тринадцатая', 'четырнадцатая', 'пятнадцатая',
                'шестнадцатая', 'семнадцатая', 'восемнадцатая', 'девятнадцатая', 'двадцатая', 'двадцатьпервая',
                'двадцатьвторая', 'двадцатьтретья', 'двадцатьчетвертая', 'двадцатьпятая', 'двадцатьшестая',
                'двадцатьседьмая', 'двадцатьвосьмая', 'двадцатьдевятая', 'тридцатая'
            ]
            roman_numbers = [
                '', 'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'xii', 'xiii', 'xiv', 'xv',
                'xvi', 'xvii', 'xviii', 'xix', 'xx', 'xxi', 'xxii', 'xxiii', 'xxiv', 'xxv', 'xxvi', 'xxvii', 'xxvii',
                'xxix', 'xxx'
            ]
            return [
                str(num),
                roman_numbers[num],
                male_ordinals[num] if male else female_ordinals[num]
            ]

        if 'obligatory_combinations' in locals():
            compound_pattern: list[str] = []
            for combination in obligatory_combinations:
                splitted_pattern: list[str] = []
                for n, item in enumerate(pattern.split()):
                    splitted_pattern.append(item if n in combination else f'*{item}')
                compound_pattern.append(' '.join(splitted_pattern))
        else:
            compound_pattern: list[str] = pattern.split(' / ')

        for pattern in compound_pattern:
            splitted_pattern: list[str] = pattern.split()
            submatches: list[str] = []
            for item in splitted_pattern:
                if item.startswith('(') and item.endswith(')') and ')' not in item[1:-1]:
                    submatches.append(parse_bracket_group(item[1:-1]))
                elif item.startswith('*(') and item.endswith(')') and ')' not in item[1:-1]:
                    submatches.append(parse_bracket_group(item[2:-1]) + [''])
                else:
                    add_empty = False
                    if item.startswith('*'):
                        item = item[1:]
                        add_empty = True
                    if re.match(r'^\d+[ия]$', item):
                        splitted_item: list[str] = parse_ordinal(item)
                    else:
                        splitted_item: list[str] = item.replace('(', ' (').replace(')', ') ').split()
                        for n, subitem in enumerate(splitted_item):
                            if subitem.startswith('(') and subitem.endswith(')') and ')' not in subitem[1:-1]:
                                splitted_item[n] = parse_bracket_group(subitem[1:-1])
                            else:
                                splitted_item[n] = subitem
                        splitted_item = permutate(splitted_item)
                    if add_empty:
                        splitted_item.append('')
                    submatches.append(splitted_item)
            matches.extend(permutate(submatches))

        matches = [remove_successive_letters(item) for item in list(set(matches)) if item]
        self.matches = ' '.join(sorted(matches))
        self.save()


class TopicEntity(models.Model):
    topic = models.ForeignKey(Topic, verbose_name='Тема', on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, verbose_name='Сущность', on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField('Место', db_index=True, default=100)
    answers_count = models.PositiveIntegerField('Количество ответов', default=0)
    initial_count = models.PositiveIntegerField('Изначальное количество ответов', default=0)

    class Meta:
        ordering = ['position']
        verbose_name_plural = 'topic entities'

    def __str__(self) -> str:
        return f'{self.topic} — {self.entity}'

    @classmethod
    def bulk_update_positions(cls, topic: Topic) -> None:
        queryset = list(cls.objects.filter(topic=topic).order_by('-answers_count'))
        for i, entity in enumerate(queryset, start=1):
            entity.position = i
        cls.objects.bulk_update(queryset, ['position'])

    def increment_answers_count(self) -> None:
        self.answers_count += 1
        self.save()

    @property
    def points(self) -> int:
        if not self.position or self.position > len(Config.points):
            return 0
        return Config.points[self.position - 1]

    @property
    def share(self) -> float:
        return round(self.answers_count / (self.topic.rounds.count() + Config.initial_rounds), 2)


class PlayerQuerySet(models.QuerySet):
    def top(self, count: int = 10):
        return self.order_by('-average_score')[:count]


class Player(models.Model):
    telegram_id = models.PositiveIntegerField('Telegram ID', unique=True)
    telegram_username = models.CharField('Telegram Username', max_length=100)
    name = models.CharField('Имя', max_length=100)
    victories = models.PositiveSmallIntegerField('Число побед', default=0)
    defeats = models.PositiveSmallIntegerField('Число поражений', default=0)
    draws = models.PositiveSmallIntegerField('Число ничьих', default=0)
    average_score = models.PositiveSmallIntegerField('Среднее число очков', default=0)
    level = models.PositiveSmallIntegerField('Уровень', default=3)
    duel_victories = models.PositiveSmallIntegerField('Число побед в дуэлях', default=0)
    duel_defeats = models.PositiveSmallIntegerField('Число поражений в дуэлях', default=0)
    duel_draws = models.PositiveSmallIntegerField('Число ничьих в дуэлях', default=0)
    duel_average_score = models.PositiveSmallIntegerField('Среднее число очков в дуэлях', default=0)
    duel_rating = models.PositiveSmallIntegerField('Рейтинг в дуэлях', default=0)
    assigned_topics = models.CharField('Список назначенных тем', max_length=20)
    referrer = models.ForeignKey(
        'Player',
        verbose_name='Реферер',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='referrals'
    )

    objects = PlayerQuerySet.as_manager()

    def __str__(self) -> str:
        return f'{self.name} id {self.telegram_id}'

    @classmethod
    def find(cls, **kwargs) -> Optional['Player']:
        if 'player_id' in kwargs:
            try:
                player = cls.objects.get(id=kwargs['player_id'])
            except cls.DoesNotExist:
                raise Http404('Игрок не найден')
        elif 'telegram_id' in kwargs:
            player, _ = cls.objects.get_or_create(
                telegram_id=kwargs['telegram_id'],
                defaults={
                    'telegram_username': kwargs['telegram_username'],
                    'name': kwargs['name']
                }
            )
        return player

    def assign_topics(self, topics: list[Topic]) -> None:
        self.assigned_topics = ' '.join([str(topic.id) for topic in topics])
        self.save()

    def clear_assigned_topics(self) -> None:
        self.assigned_topics = ''
        self.save()

    def update_statistics(self) -> None:
        finished_rounds = self.rounds.finished()
        average_score = finished_rounds.aggregate(avg=Avg('score1'))['avg']
        self.average_score = round(average_score)
        self.victories = finished_rounds.filter(score1__gt=F('score2')).count()
        self.defeats = finished_rounds.filter(score1__lt=F('score2')).count()
        self.draws = finished_rounds.filter(score1=F('score2')).count()
        for i, value in enumerate(Config.topic_levels):
            if self.average_score < value:
                self.level = i
                break
        self.save()

    @property
    def displayed_name(self) -> str:
        if self.name:
            return self.name
        return self.telegram_username

    @property
    def position(self) -> int:
        return Player.objects.filter(average_score__gt=self.average_score).count() + 1


class RoundQuerySet(models.QuerySet):
    def finished(self):
        return self.filter(finished_at__isnull=False)

    def last_finished(self, count: int):
        return self.finished().order_by('-finished_at')[:count]


class Round(models.Model):
    player1 = models.ForeignKey(Player, verbose_name='Игрок 1', on_delete=models.PROTECT, related_name='rounds')
    player2 = models.ForeignKey(
        Player,
        verbose_name='Игрок 2',
        on_delete=models.PROTECT,
        related_name='guest_rounds',
        null=True,
        blank=True
    )
    topic = models.ForeignKey(Topic, verbose_name='Тема', on_delete=models.PROTECT, related_name='rounds')
    duel = models.BooleanField('Дуэль', db_index=True, default=False)
    score1 = models.PositiveSmallIntegerField('Очки первого игрока', default=0)
    score2 = models.PositiveSmallIntegerField('Очки второго игрока', default=0)
    started_at = models.DateTimeField('Начало', auto_now_add=True)
    finished_at = models.DateTimeField('Окончание', null=True, blank=True)
    bot_answers = models.TextField('Список возможных ответов бота', default='{}')
    player1_feedback = models.TextField('Обратная связь от игрока 1')
    player2_feedback = models.TextField('Обратная связь от игрока 1')

    objects = RoundQuerySet.as_manager()

    class Meta:
        unique_together = ['player1', 'player2', 'topic']

    def __str__(self) -> str:
        player2 = self.player2 if self.player2 else 'bot'
        return f'{self.topic} — {self.player1} vs {player2}'

    def add_feedback(self, feedback: str, player: int = 1) -> None:
        setattr(self, f'player{player}_feedback', feedback)
        self.save()

    def finish(self, score1: int = 0, score2: int = 0, abort: bool = False) -> None:
        if self.finished_at:
            return
        self.finished_at = timezone.now()
        if not abort:
            self.score1 = score1
            self.score2 = score2
            self.save()
            self.topic.update_statistics()
            self.player1.update_statistics()
        else:
            self.save()

    def get_bot_answer(self) -> tuple[str, TopicEntity]:
        topic_entity_id, bot_answer = list(json.loads(self.bot_answers).items())[0]
        topic_entity = TopicEntity.objects.get(id=topic_entity_id)
        Answer.get_or_create(round=self, topic_entity=topic_entity, text=bot_answer, player=2)
        return bot_answer, topic_entity

    def shorten_bot_answers(self, topic_entity_id: int) -> None:
        bot_answers = json.loads(self.bot_answers)
        if str(topic_entity_id) in bot_answers:
            del bot_answers[str(topic_entity_id)]
        self.update_bot_answers(json.dumps(bot_answers, ensure_ascii=False))

    def update_bot_answers(self, bot_answers: str = '') -> None:
        if bot_answers:
            self.bot_answers = bot_answers
        else:
            self.bot_answers = self.topic.bot_answers
        self.save()

    @property
    def attempts_left(self) -> int:
        return max(0, int((10 - self.answers.count()) / 2))

    @property
    def outcome(self) -> str:
        if self.score1 == self.score2:
            return '='
        elif self.score1 > self.score2:
            return '1'
        return '2'

    @admin.display
    def player1_answers(self) -> str:
        answers = ', '.join(f'{answer.text} ({answer.position})' for answer in self.answers.filter(player=1))
        answers = answers.replace(' (None)', '')
        return answers

    @admin.display
    def player2_answers(self) -> str:
        answers = ', '.join(f'{answer.text} ({answer.position})' for answer in self.answers.filter(player=2))
        answers = answers.replace(' (None)', '')
        return answers


class Answer(models.Model):
    round = models.ForeignKey(Round, verbose_name='Раунд', on_delete=models.PROTECT, related_name='answers')
    topic_entity = models.ForeignKey(
        TopicEntity,
        on_delete=models.PROTECT,
        related_name='answers',
        null=True,
        blank=True
    )
    player = models.PositiveSmallIntegerField('Игрок', choices=[(1, 1), (2, 2)], default=1)
    text = models.TextField('Ответ')
    position = models.PositiveSmallIntegerField('Место', null=True, blank=True)
    sent_at = models.DateTimeField('Отправлен', auto_now_add=True)

    def __str__(self) -> str:
        return f'{self.round} — {self.text}'

    @classmethod
    def get_or_create(
            cls,
            round: Round,
            topic_entity: Optional[TopicEntity] = None,
            text: str = '',
            player: int = 1
    ) -> bool:
        if topic_entity:
            _, created = cls.objects.get_or_create(
                round=round,
                topic_entity=topic_entity,
                defaults={'player': player, 'text': text, 'position': topic_entity.position}
            )
            round.shorten_bot_answers(topic_entity.id)
            topic_entity.increment_answers_count()
        else:
            _, created = cls.objects.get_or_create(
                round=round,
                text=text
            )
        return created