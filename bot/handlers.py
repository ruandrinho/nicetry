import asyncio
import logging
import uuid
from contextlib import suppress
from logging.handlers import RotatingFileHandler
from random import choice, sample

import aiohttp
from aiogram import Router, F, html
from aiogram.client.bot import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, Text, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.fsm.storage.redis import Redis
from aiogram.types import CallbackQuery, Message

from config import Messages, Images, ADMIN_ID, API, OPEN, LOG_FILE
from utils import (
    format_hits,
    format_rating,
    format_score,
    get_keyboard
)

game_router = Router()

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s: %(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(LOG_FILE, maxBytes=1024*1024, backupCount=10)
    ]
)
logger = logging.getLogger(__name__)

redis = Redis(host='redis', decode_responses=True)


class GameStates(StatesGroup):
    main = State()
    duel_or_chatgpt = State()
    topic = State()
    duel_topic = State()
    points_or_hits = State()
    duel_points_or_hits = State()
    answer = State()
    feedback = State()
    interruption = State()
    sleep = State()


@game_router.message(Command('spam'), F.from_user.id == ADMIN_ID)
async def handle_command_spam(message: Message, state: FSMContext, bot: Bot, command: CommandObject = None):
    group, message = command.args.split(' ', 1)
    if group not in ['ALL', 'INACTIVE']:
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'{API}/players',
            params={
                'group': group,
            }
        ) as response:
            decoded_response = await response.json()
            log_message = 'GAME Get players'
            if response.status != 200:
                logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                await handle_error_response(message, state, decoded_response['detail'])
                return
            logger.info(log_message)

    for player in decoded_response:
        with suppress(TelegramBadRequest):
            logger.info(f'SPAM Send to {player["name_with_id"]}')
            await bot.send_message(player['telegram_id'], message, disable_notification=True)


@game_router.message(Command('start'), StateFilter(default_state))
async def handle_command_start(
        message: Message,
        state: FSMContext,
        bot: Bot,
        callback: CallbackQuery = None,
        after_results: bool = False
) -> None:
    if await check_closed_game(message, bot):
        return

    from_user = callback.from_user if callback else message.from_user
    name = ' '.join([from_user.first_name or '', from_user.last_name or '']).strip()
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{API}/player',
            json={
                'telegram_id': from_user.id,
                'telegram_username': from_user.username,
                'name': name
            }
        ) as response:
            decoded_response = await response.json()
            log_message = f'GAME Join {decoded_response["name_with_id"]}'
            if response.status != 200:
                logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                await handle_error_response(message, state, decoded_response['detail'])
                return
            logger.info(log_message)

    new_message = await message.answer_photo(
        Images.main,
        Messages.welcome,
        reply_markup=await get_keyboard([['game', 'rules', 'rating']])
    )
    await state.update_data(new_message_id=new_message.message_id, player=decoded_response)

    if after_results:
        await message.edit_reply_markup(reply_markup=None)
    else:
        await message.delete()

    if callback:
        await callback.answer()

    await state.set_state(GameStates.main)


@game_router.message(Command('start'))
async def handle_interrupting_start(message: Message, state: FSMContext) -> None:
    await message.answer(
        Messages.confirm_interruption,
        reply_markup=await get_keyboard([['main', 'go_on']])
    )
    await state.update_data(interrupting_message_id=message.message_id, backup_state=await state.get_state())
    await state.set_state(GameStates.interruption)


@game_router.callback_query(Text('main'), GameStates.interruption)
async def handle_interruption_confirmation(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    # await redis.delete('duel_id')
    user_data = await state.get_data()

    with suppress(TelegramBadRequest):
        if 'interrupting_message_id' in user_data:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=user_data['interrupting_message_id'])
        if 'new_message_id' in user_data:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=user_data['new_message_id'])
        if 'pinned_message_id' in user_data:
            await bot.unpin_chat_message(chat_id=callback.message.chat.id, message_id=user_data['pinned_message_id'])

    if user_data.get('backup_state') == GameStates.answer:
        game_data = await redis.json().get(user_data['game_id'])
        if 'round_id' in user_data and game_data and 'player1' in game_data and 'player2' in game_data:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{API}/finish',
                    json={
                        'round_id': user_data['round_id'],
                        'abort_side': user_data['side'],
                        'score1': game_data['player1']['score'],
                        'score2': game_data['player2']['score'],
                        'hits1': game_data['player1']['hits'],
                        'hits2': game_data['player2']['hits']
                    }
                ) as response:
                    decoded_response = await response.json()
                    log_message = f'GAME Abort round {user_data["round_id"]}'\
                                  f' • Player {user_data["player"]["name_with_id"]}'
                    if response.status != 200:
                        logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                        await handle_error_response(callback.message, state, decoded_response['detail'])
                        await callback.answer()
                        return
                    logger.info(log_message)
        await state.set_data({'player': user_data['player'], 'round_is_finished': True})
    else:
        await state.set_data({})

    if 'game_id' in user_data:
        await redis.json().delete(user_data['game_id'])
    await callback.answer()
    await handle_command_start(message=callback.message, state=state, bot=bot, callback=callback)


@game_router.callback_query(Text('go_on'), GameStates.interruption)
async def handle_interruption_cancel(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    user_data = await state.get_data()
    await callback.message.delete()
    await callback.answer()
    with suppress(TelegramBadRequest):
        if 'interrupting_message_id' in user_data:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=user_data['interrupting_message_id'])
    await state.set_state(user_data['backup_state'])


@game_router.callback_query(Text('main'))
async def handle_query_main(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    # await redis.delete('duel_id')
    user_data = await state.get_data()
    after_results = False
    if user_data.get('round_is_finished'):
        await state.update_data(round_is_finished=False)
        after_results = True
    await callback.answer()
    await handle_command_start(
        message=callback.message,
        state=state,
        bot=bot,
        callback=callback,
        after_results=after_results
    )


@game_router.callback_query(Text('rules'), GameStates.main)
async def handle_query_rules(callback: CallbackQuery, state: FSMContext) -> None:
    new_message = await callback.message.answer_photo(
        Images.rules,
        Messages.rules,
        reply_markup=await get_keyboard([['game', 'rating', 'main']])
    )
    await state.update_data(new_message_id=new_message.message_id)
    await callback.message.delete()
    await callback.answer()


# TODO duel rating button and handler
@game_router.callback_query(Text('rating'), GameStates.main)
async def handle_query_rating(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = await state.get_data()

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'{API}/rating'
        ) as response:
            decoded_response = await response.json()
            log_message = 'GAME Get rating'
            if response.status != 200:
                logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                await handle_error_response(callback.message, state, decoded_response['detail'])
                await callback.answer()
                return
            logger.info(log_message)

    formatted_rating = await format_rating(decoded_response, user_data['player'])
    new_message = await callback.message.answer(
        f'{Messages.rating_formula}\n\n{formatted_rating}',
        reply_markup=await get_keyboard([['game', 'rules', 'main']])
    )
    await state.update_data(new_message_id=new_message.message_id)
    await callback.message.delete()
    await callback.answer()


@game_router.callback_query(Text('game'), GameStates.main)
@game_router.callback_query(Text('game_again'), GameStates.main)
async def handle_query_game(callback: CallbackQuery, state: FSMContext, bot: Bot, after_results: bool = False) -> None:
    if await check_closed_game(callback.message, bot):
        return

    user_data = await state.get_data()
    if user_data.get('round_is_finished'):
        await state.update_data(round_is_finished=False)
        after_results = True

    if after_results:
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.message.delete()
    await callback.answer()

    duel_id = await redis.get('duel_id')
    if duel_id:
        game_data = await redis.json().get(duel_id)
        if game_data and 'player1' in game_data:
            new_message = await callback.message.answer(
                Messages.duel_call.replace('DUELIST', game_data['player1']['displayed_name']),
                reply_markup=await get_keyboard([['call_duel'], ['chatgpt']])
            )
            await state.update_data(new_message_id=new_message.message_id, game_id=duel_id)
            await state.set_state(GameStates.duel_or_chatgpt)
            return

    new_message = await callback.message.answer(
        Messages.create_duel,
        reply_markup=await get_keyboard([['create_duel'], ['chatgpt']])
    )
    await state.update_data(new_message_id=new_message.message_id)
    await state.set_state(GameStates.duel_or_chatgpt)


@game_router.callback_query(Text('create_duel'), GameStates.duel_or_chatgpt)
async def handle_query_create_duel(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_data = await state.get_data()

    game_id = str(uuid.uuid4())
    game_data = {'player1': user_data['player']}
    await redis.set('duel_id', game_id)
    await redis.json().set(game_id, '$', game_data)
    await state.update_data(game_id=game_id, side=1, opponent_key='player2', self_key='player1')

    new_message = await callback.message.answer(
        Messages.duel_start_waiting,
        reply_markup=await get_keyboard([['cancel_duel']])
    )
    await state.update_data(new_message_id=new_message.message_id)

    await callback.message.delete()
    await callback.answer()
    await state.set_state(GameStates.duel_topic)


@game_router.callback_query(Text('cancel_duel'), GameStates.duel_topic)
async def handle_query_cancel_duel(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    duel_id = await redis.get('duel_id')
    await redis.delete('duel_id')
    await redis.json().delete(duel_id)
    await state.set_data({})
    await callback.answer()
    await handle_command_start(message=callback.message, state=state, bot=bot, callback=callback)


@game_router.callback_query(Text('chatgpt'), GameStates.duel_or_chatgpt)
@game_router.callback_query(Text('call_duel'), GameStates.duel_or_chatgpt)
async def handle_query_duel_or_chatgpt(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    duel = callback.data == 'call_duel'
    user_data = await state.get_data()

    if duel:
        await redis.delete('duel_id')
        game_id = user_data['game_id']
        game_data = await redis.json().get(game_id)
        game_data.update({'player2': user_data['player'], 'duel': True})
        game_data['player1']['avatar'], game_data['player2']['avatar'] = sample(Messages.Emojis.avatars, 2)
        await state.update_data(opponent_key='player1', self_key='player2')
    else:
        game_id = str(uuid.uuid4())
        await state.update_data(game_id=game_id, self_key='player1')
        game_data = {'player1': user_data['player'], 'player2': {'id': 0}, 'duel': False}
        game_data['player1']['avatar'], game_data['player2']['avatar'] = Messages.Emojis.human, Messages.Emojis.chatgpt
        await redis.json().set(game_id, '$', game_data)

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'{API}/random-topics',
            params={
                'player1_id': game_data['player1']['id'],
                'player2_id': game_data['player2']['id'],
            }
        ) as response:
            decoded_response = await response.json()
            mode_caption = 'Duel' if duel else 'Single'
            log_message = f'GAME {mode_caption} Get random topics • Player {user_data["player"]["name_with_id"]}'
            if response.status != 200:
                logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                await handle_error_response(callback.message, state, decoded_response['detail'])
                await callback.answer()
                return
            logger.info(log_message)

    # TODO 1 or 2 topics
    game_data['topics'] = decoded_response
    await redis.json().set(game_id, '$', game_data)

    buttons = [[(topic['title'], f'id{topic["id"]}')] for topic in game_data['topics']]
    buttons.append(['main'])
    joined_topics = ', '.join(topic['title'] for topic in game_data['topics'])
    blank_message = Messages.choose_duel_topic1 if duel else Messages.choose_topic
    new_message = await callback.message.answer(
        blank_message.replace('TOPICS', joined_topics),
        reply_markup=await get_keyboard(buttons)
    )
    await state.update_data(new_message_id=new_message.message_id, game_id=game_id)
    with suppress(TelegramBadRequest):
        await callback.message.delete()
    await callback.answer()
    await state.set_state(GameStates.duel_topic if duel else GameStates.topic)


@game_router.callback_query(Text(startswith='id'), GameStates.topic)
async def handle_query_topic(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = await state.get_data()
    game_data = await redis.json().get(user_data['game_id'])

    if 'topic' not in game_data:
        topic_id = int(callback.data.replace('id', ''))
        game_data['topic'] = next(topic for topic in game_data['topics'] if topic['id'] == topic_id)
        del game_data['topics']
        await redis.json().set(user_data['game_id'], '$', game_data)

    new_message = await callback.message.answer(
        Messages.choose_mode,
        reply_markup=await get_keyboard([['modepoints', 'modehits']])
    )
    await state.update_data(new_message_id=new_message.message_id)
    await callback.message.delete()
    await callback.answer()
    await state.set_state(GameStates.points_or_hits)


@game_router.callback_query(Text(startswith='id'), GameStates.duel_topic)
async def handle_query_duel_topic(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    user_data = await state.get_data()
    game_data = await redis.json().get(user_data['game_id'])
    # logger.debug(user_data)
    # logger.debug(game_data)

    topic_id = int(callback.data.replace('id', ''))
    if 'topics' in game_data and len(game_data['topics']) == 3:
        game_data['topics'] = [topic for topic in game_data['topics'] if topic['id'] != topic_id]
        new_message = await callback.message.answer(Messages.duel_opponent_waiting)
        await state.update_data(new_message_id=new_message.message_id)
        buttons = [[(topic['title'], f'id{topic["id"]}')] for topic in game_data['topics']]
        buttons.append(['main'])
        joined_topics = ', '.join(topic['title'] for topic in game_data['topics'])
        await bot.send_message(
            game_data[user_data['opponent_key']]['telegram_id'],
            Messages.choose_duel_topic2.replace('TOPICS', joined_topics),
            reply_markup=await get_keyboard(buttons)
        )
        with suppress(TelegramBadRequest):
            await bot.delete_message(
                chat_id=game_data[user_data['opponent_key']]['telegram_id'],
                message_id=game_data[user_data['opponent_key']]['new_message_id'],
            )
        await state.set_state(GameStates.points_or_hits)
        # TODO 2 or 1
        await redis.json().set(user_data['game_id'], '$', game_data)
        await callback.message.delete()
        await callback.answer()
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'{API}/topic',
            params={
                'topic_id': topic_id,
            }
        ) as response:
            decoded_response = await response.json()
            log_message = f'GAME Duel Get topic • Player {user_data["player"]["name_with_id"]}'
            if response.status != 200:
                logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                await handle_error_response(callback.message, state, decoded_response['detail'])
                await callback.answer()
                return
            logger.info(log_message)

    game_data['topic'] = decoded_response
    pinned_message = await callback.message.answer(f'Тема: {game_data["topic"]["title"]}')
    await pinned_message.pin(disable_notification=True)
    new_message = await callback.message.answer(Messages.duel_opponent_waiting)
    await state.update_data(new_message_id=new_message.message_id, pinned_message_id=pinned_message.message_id)
    game_data[user_data['self_key']]['pinned_message_id'] = pinned_message.message_id
    await bot.send_message(
        game_data[user_data['opponent_key']]['telegram_id'],
        Messages.choose_duel_mode.replace('TOPIC', decoded_response['title']),
        reply_markup=await get_keyboard([['modepoints', 'modehits']])
    )
    await state.set_state(GameStates.answer)

    await redis.json().set(user_data['game_id'], '$', game_data)
    await callback.message.delete()
    await callback.answer()


@game_router.callback_query(Text(startswith='mode'), GameStates.points_or_hits)
async def handle_query_mode(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    user_data = await state.get_data()
    game_data = await redis.json().get(user_data['game_id'])
    game_data['hits_mode'] = callback.data == 'modehits'

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{API}/round',
            json={
                'player1_id': game_data['player1']['id'],
                'player2_id': game_data['player2']['id'],
                'topic_id': game_data['topic']['id'],
                'hits_mode': game_data['hits_mode']
            }
        ) as response:
            decoded_response = await response.json()
            mode_caption = 'Duel' if game_data['duel'] else 'Single'
            log_message = f'GAME {mode_caption} Start duel round {decoded_response["id"]}'\
                          f' • Player {user_data["player"]["name_with_id"]}'\
                          f' • Topic {game_data["topic"]["title"]} • {callback.data}'
            if response.status != 200:
                logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                await handle_error_response(callback.message, state, decoded_response['detail'])
                await callback.answer()
                return
            logger.info(log_message)

    game_data['player1'].update({'hits': 0, 'score': 0})
    game_data['player2'].update({'hits': 0, 'score': 0})
    game_data.update({
        'round_id': decoded_response['id'],
        'hits': [],
        'turn': 2 if game_data['duel'] else 1
    })

    pinned_message = await callback.message.answer(f'Тема: {game_data["topic"]["title"]}')
    await pinned_message.pin(disable_notification=True)
    new_message = await callback.message.answer(
        Messages.hits_mode_first if game_data['hits_mode'] else Messages.attempt1
    )
    await state.update_data(
        new_message_id=new_message.message_id,
        pinned_message_id=pinned_message.message_id,
        round_id=game_data['round_id'],
        side=2 if game_data['duel'] else 1
    )
    game_data[user_data['self_key']]['pinned_message_id'] = pinned_message.message_id
    await redis.json().set(user_data['game_id'], '$', game_data)

    if game_data['duel']:
        with suppress(TelegramBadRequest):
            if 'new_message_id' in user_data:
                await bot.delete_message(chat_id=callback.message.chat.id, message_id=user_data['new_message_id'])
        await bot.send_message(
            game_data[user_data['opponent_key']]['telegram_id'],
            Messages.hits_mode_chosen if game_data['hits_mode'] else Messages.points_mode_chosen
        )

    await callback.message.delete()
    await callback.answer()
    await state.set_state(GameStates.answer)


@game_router.message(F.text, GameStates.answer)
async def handle_message_answer(message: Message, state: FSMContext, bot: Bot) -> None:
    user_data = await state.get_data()
    game_data = await redis.json().get(user_data['game_id'])
    if not user_data.get('round_id'):
        user_data['round_id'] = game_data.get('round_id')
        await state.update_data(round_id=user_data['round_id'])

    if user_data['side'] != game_data['turn']:
        return

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{API}/answer',
            json={
                'round_id': user_data['round_id'],
                'answer': message.text,
                'side': user_data['side']
            }
        ) as response:
            decoded_response = await response.json()
            mode_caption = 'Duel' if game_data['duel'] else 'Single'
            log_message = f'GAME {mode_caption} Send answer "{message.text}"'\
                          f' • Player {user_data["player"]["name_with_id"]}'\
                          f' • Round {user_data["round_id"]}'
            if response.status != 200:
                logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                await message.answer(decoded_response['detail'])
                return
            logger.info(log_message)

    await state.update_data(ambiguous_answer=False)
    if decoded_response['entities'] and len(decoded_response['entities']) > 1:
        await state.update_data(ambiguous_answer=message.text)
        buttons = [[(entity['title'], f'id{entity["id"]}')] for entity in decoded_response['entities']]
        await message.answer(
            Messages.ambiguity,
            reply_markup=await get_keyboard(buttons)
        )
        return

    await handle_attempt(message, state, bot, decoded_response)


@game_router.callback_query(Text(startswith='id'), GameStates.answer)
async def handle_query_answer(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    user_data = await state.get_data()
    logger.debug(user_data)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{API}/answer',
            json={
                'round_id': user_data['round_id'],
                'answer': user_data['ambiguous_answer'],
                'side': user_data['side'],
                'entity_id': int(callback.data.replace('id', ''))
            }
        ) as response:
            decoded_response = await response.json()
            log_message = f'GAME Specify answer "{user_data["ambiguous_answer"]}"'\
                          f' • Player {user_data["player"]["name_with_id"]} • Round {user_data["round_id"]}'
            if response.status != 200:
                logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                await callback.message.answer(decoded_response['detail'])
                await callback.message.delete()
                await callback.answer()
                return
            logger.info(log_message)

    await handle_attempt(callback.message, state, bot, decoded_response)

    await callback.message.delete()
    await callback.answer()


async def handle_attempt(message: Message, state: FSMContext, bot: Bot, attempt_response: dict):
    user_data = await state.get_data()
    game_data = await redis.json().get(user_data['game_id'])

    game_data['new_hit'] = False
    if attempt_response['entities']:
        entity = attempt_response['entities'][0]
        if entity['points']:
            game_data['new_hit'] = True

    answer_for_opponent = user_data['ambiguous_answer'] if user_data['ambiguous_answer'] else message.text
    message_for_opponent = Messages.opponent_answer.replace('ANSWER', answer_for_opponent)
    if game_data['new_hit']:
        if game_data['duel']:
            await bot.send_message(
                game_data[user_data['opponent_key']]['telegram_id'],
                message_for_opponent
            )
        await handle_hit(message, state, entity, bot)
        game_data = await redis.json().get(user_data['game_id'])
    elif not attempt_response['skipped']:
        await message.answer(Messages.miss)
        if game_data['duel']:
            message_for_opponent += Messages.miss_addition
            await bot.send_message(
                game_data[user_data['opponent_key']]['telegram_id'],
                message_for_opponent
            )
    else:
        if game_data['duel']:
            await bot.send_message(
                game_data[user_data['opponent_key']]['telegram_id'],
                Messages.opponent_skipped
            )

    if not game_data['duel']:
        game_data['turn'] = 2
        await redis.json().set(user_data['game_id'], '$', game_data)
        await handle_chatgpt_answer(message, state, bot, attempt_response['chatgpt_answer'])
        game_data = await redis.json().get(user_data['game_id'])
    await handle_game_progress(message, state, bot, attempt_response['attempt'])

    game_data['turn'] = 2 if game_data['turn'] == 1 else 1
    await redis.json().set(user_data['game_id'], '$', game_data)


async def handle_hit(message: Message, state: FSMContext, entity: dict, bot: Bot = None) -> None:
    user_data = await state.get_data()
    game_data = await redis.json().get(user_data['game_id'])
    player_key = f'player{game_data["turn"]}'

    hit_record = {
        'position': entity['position'],
        'answer': entity['title'],
        'points': entity['points'],
        'player': game_data['turn']
    }
    game_data['hits'].append(hit_record)
    game_data[player_key]['score'] += hit_record['points']
    game_data[player_key]['hits'] += 1
    await redis.json().set(user_data['game_id'], '$', game_data)

    formatted_hits = await format_hits(game_data)
    hit_message = f'{choice(Messages.hit)}\n\n{formatted_hits}'
    new_message = await message.answer(hit_message)
    await state.update_data(new_message_id=new_message.message_id)
    if game_data['duel']:
        await bot.send_message(game_data[user_data['opponent_key']]['telegram_id'], hit_message)

    with suppress(TelegramBadRequest):
        score_message = await format_score(game_data)
        await bot.edit_message_text(
            text=score_message,
            chat_id=message.chat.id,
            message_id=user_data['pinned_message_id']
        )
        if game_data['duel']:
            await bot.edit_message_text(
                text=score_message,
                chat_id=game_data[user_data['opponent_key']]['telegram_id'],
                message_id=game_data[user_data['opponent_key']]['pinned_message_id']
            )


async def handle_chatgpt_answer(message: Message, state: FSMContext, bot: Bot, answer: dict) -> None:
    await state.set_state(GameStates.sleep)
    user_data = await state.get_data()
    game_data = await redis.json().get(user_data['game_id'])
    game_data['turn'] = 2
    await redis.json().set(user_data['game_id'], '$', game_data)

    chatgpt_answer_message = Messages.chatgpt_answer.replace('ANSWER', answer['text'])
    if not answer['entity']['points']:
        chatgpt_answer_message += Messages.miss_addition
    await bot.send_chat_action(message.chat.id, 'typing')
    await asyncio.sleep(1)
    await message.answer(chatgpt_answer_message)
    await asyncio.sleep(1)

    if answer['entity']['points']:
        await handle_hit(message, state, answer['entity'], bot)


async def handle_game_progress(message: Message, state: FSMContext, bot: Bot, attempt: int) -> None:
    user_data = await state.get_data()
    game_data = await redis.json().get(user_data['game_id'])

    game_over = False
    if game_data['hits_mode']:
        if attempt % 2 and (game_data['player1']['hits'] == 3 or game_data['player2']['hits'] == 3):
            game_over = True
            attempt_message = Messages.attempt6
        elif attempt == 3 or attempt == 4:
            attempt_message = Messages.hits_mode_second
        else:
            attempt_message = choice(Messages.hits_mode_attempt)
    else:
        if attempt == 11:
            game_over = True
        attempt_message = getattr(Messages, f'attempt{attempt}')
    if game_data['duel']:
        await bot.send_message(game_data[user_data['opponent_key']]['telegram_id'], attempt_message)
    else:
        new_message = await message.answer(attempt_message)
        await state.update_data(new_message_id=new_message.message_id)
    await state.set_state(GameStates.answer)

    if not game_over:
        if game_data['duel']:
            await message.answer(Messages.duel_opponent_waiting)
        return

    await state.set_state(GameStates.sleep)

    score1, score2 = game_data['player1']['score'], game_data['player2']['score']
    hits1, hits2 = game_data['player1']['hits'], game_data['player2']['hits']
    if game_data['hits_mode']:
        outcome = f'{hits1}:{hits2}'
        if hits1 == hits2:
            outcome += f' (по очкам {score1}:{score2})'
            if score1 == score2:
                outcome_message = Messages.outcome_draw
            elif score1 > score2:
                outcome_message = Messages.outcome_player1 if game_data['duel'] else Messages.outcome_victory
            else:
                outcome_message = Messages.outcome_player2 if game_data['duel'] else Messages.outcome_defeat
        elif hits1 > hits2:
            outcome_message = Messages.outcome_player1 if game_data['duel'] else Messages.outcome_victory
        else:
            outcome_message = Messages.outcome_player2 if game_data['duel'] else Messages.outcome_defeat
    else:
        outcome = f'{score1}:{score2}'
        if score1 == score2:
            outcome_message = Messages.outcome_draw
        elif score1 > score2:
            outcome_message = Messages.outcome_player1 if game_data['duel'] else Messages.outcome_victory
        else:
            outcome_message = Messages.outcome_player2 if game_data['duel'] else Messages.outcome_defeat
    outcome_message = outcome_message.replace('RESULT', html.bold(outcome))
    if 'PLAYER1' in outcome_message:
        outcome_message = outcome_message.replace('PLAYER1', html.bold(game_data['player1']['displayed_name']))
    if 'PLAYER2' in outcome_message:
        outcome_message = outcome_message.replace('PLAYER2', html.bold(game_data['player2']['displayed_name']))
    rating_message = ''
    formatted_results = await format_hits(game_data, results=True)

    with suppress(TelegramBadRequest):
        await bot.unpin_chat_message(chat_id=message.chat.id, message_id=user_data['pinned_message_id'])
        if game_data['duel']:
            await bot.unpin_chat_message(
                chat_id=game_data[user_data['opponent_key']]['telegram_id'],
                message_id=game_data[user_data['opponent_key']]['pinned_message_id']
            )

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{API}/finish',
            json={
                'round_id': user_data['round_id'],
                'score1': score1,
                'score2': score2,
                'hits1': hits1,
                'hits2': hits2
            }
        ) as response:
            decoded_response = await response.json()
            log_message = f'GAME Finish round {user_data["round_id"]} • {outcome}'
            if response.status != 200:
                logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                await handle_error_response(message, state, decoded_response['detail'])
                return
            logger.info(log_message)

    rating, position = decoded_response[f'rating{user_data["side"]}'], decoded_response[f'position{user_data["side"]}']
    rating_message = Messages.rating_change.replace('RATING', html.bold(str(rating))).\
        replace('POSITION', html.bold(str(position)))

    await redis.json().delete(user_data['game_id'])
    await state.set_data({
        'player': user_data['player'],
        'round_id': user_data['round_id'],
        'round_is_finished': True,
    })

    await bot.send_chat_action(message.chat.id, 'typing')
    await asyncio.sleep(2)
    await message.answer_photo(
        Images.results,
        f'{outcome_message}\n\n{rating_message}\n\n{formatted_results}',
        reply_markup=await get_keyboard([['main', 'game_again'], ['feedback', 'invite']])
    )

    if game_data['duel']:
        opponent_side = 2 if user_data['side'] == 1 else 1
        rating, position = decoded_response[f'rating{opponent_side}'], decoded_response[f'position{opponent_side}']
        rating_message = Messages.rating_change.replace('RATING', html.bold(str(rating))).\
            replace('POSITION', html.bold(str(position)))
        await bot.send_photo(
            chat_id=game_data[user_data['opponent_key']]['telegram_id'],
            photo=Images.results,
            caption=f'{outcome_message}\n\n{rating_message}\n\n{formatted_results}',
            reply_markup=await get_keyboard([['main', 'game_again'], ['feedback', 'invite']])
        )

    await state.set_state(GameStates.main)


@game_router.callback_query(Text('feedback'))
async def handle_feedback(callback: CallbackQuery, state: FSMContext) -> None:
    new_message = await callback.message.answer(Messages.feedback)
    await state.update_data(new_message_id=new_message.message_id)
    await callback.message.delete()
    await callback.answer()
    await state.set_state(GameStates.feedback)


# TODO player2
@game_router.message(F.text, GameStates.feedback)
async def handle_feedback_message(message: Message, state: FSMContext) -> None:
    user_data = await state.get_data()
    async with aiohttp.ClientSession() as session:
        async with session.put(
            f'{API}/round',
            json={
                'round_id': user_data['round_id'],
                'feedback': message.text,
            }
        ) as response:
            decoded_response = await response.json()
            log_message = f'GAME Send feedback {message.text}" • Player {user_data["player"]["name_with_id"]}'\
                          f' • Round {user_data["round_id"]}'
            if response.status != 200:
                logger.warning(f'{log_message} STATUS {response.status} {decoded_response["detail"]}')
                await handle_error_response(message, state, decoded_response['detail'])
                return
            logger.info(log_message)

    await message.answer(
        Messages.feedback_thanks,
        reply_markup=await get_keyboard([['main', 'invite']])
    )
    await state.set_state(GameStates.main)


@game_router.message(F.text, GameStates.sleep)
async def handle_sleep(message: Message, state: FSMContext) -> None:
    pass


@game_router.message(F.text)
async def handle_any_message(message: Message, state: FSMContext) -> None:
    await handle_default(message, state)


@game_router.callback_query()
async def handle_any_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await handle_default(callback.message, state)


async def handle_default(message: Message, state: FSMContext) -> None:
    await message.answer(Messages.default)


async def handle_error_response(message: Message, state: FSMContext, error_message: str) -> None:
    await message.answer(
        error_message,
        reply_markup=await get_keyboard([['main']])
    )
    await message.delete()
    await state.set_state(GameStates.main)


async def check_closed_game(message: Message, bot: Bot) -> bool:
    alert_queue = await redis.get('alert_queue')
    if OPEN:
        if not alert_queue:
            return False
        alert_queue = set(map(int, alert_queue.split()))
        for id in alert_queue:
            await bot.send_message(id, Messages.open, disable_notification=True)
            logger.info(f'GAME Open alert sent to user {id}')
        await redis.set('alert_queue', '')
        return False
    await message.answer(Messages.closed)
    alert_queue = message.chat.id if not alert_queue else f'{alert_queue} {message.chat.id}'
    await redis.set('alert_queue', alert_queue)
    logger.info(f'GAME Queued user {message.chat.id}')
    return True
