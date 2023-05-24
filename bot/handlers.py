import asyncio
import logging
from contextlib import suppress
from random import choice, randint

import aiohttp
from aiogram import Router, F, html
from aiogram.client.bot import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, Text, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.fsm.storage.redis import Redis
from aiogram.types import CallbackQuery, Message

from config import Messages, Images, ADMIN_ID, API, OPEN
from utils import (
    decode_referral,
    encode_referral,
    format_hits,
    format_player,
    format_rating,
    get_keyboard
)

game_router = Router()

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s: %(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

redis = Redis(host='redis', decode_responses=True)


class GameStates(StatesGroup):
    main = State()
    topic = State()
    answer = State()
    feedback = State()
    interruption = State()


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
            if response.status != 200:
                decoded_response = await response.json()
                await handle_error_response(message, state, decoded_response['detail'])
                logger.warning(f'GAME Getting players: {decoded_response["detail"]}')
                return
            players = await response.json()
    for player in players:
        with suppress(TelegramBadRequest):
            logger.info(f'SPAM Message sent to {player["displayed_name"]}')
            await bot.send_message(player['id'], message, disable_notification=True)


@game_router.message(Command('start'), StateFilter(default_state))
async def handle_command_start(
        message: Message,
        state: FSMContext,
        bot: Bot,
        callback: CallbackQuery = None,
        command: CommandObject = None,
        after_results: bool = False
) -> None:
    if await check_closed_game(message, bot):
        return
    if command and command.args:
        challenged_topic_id, referrer_id = await decode_referral(command.args)
        if challenged_topic_id > 0 and challenged_topic_id < 2000:
            await state.update_data(challenged_topic_id=challenged_topic_id, referrer_id=referrer_id)
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
            player = await response.json()
            await state.update_data(player=player)
            logger.info(f'GAME Joined {format_player(player)}')
    new_message = await message.answer_photo(
        Images.main,
        Messages.welcome,
        reply_markup=await get_keyboard([['game', 'rules', 'rating']])
    )
    await state.update_data(new_message_id=new_message.message_id)
    if after_results:
        await message.edit_reply_markup(reply_markup=None)
    else:
        await message.delete()
    await state.set_state(GameStates.main)


@game_router.message(Command('start'))
async def handle_interrupting_start(message: Message, state: FSMContext) -> None:
    await message.answer(
        Messages.confirm_interruption,
        reply_markup=await get_keyboard([['main', 'go_on']])
    )
    await state.update_data(backup_state=await state.get_state())
    await state.update_data(interrupting_message_id=message.message_id)
    await state.set_state(GameStates.interruption)


@game_router.callback_query(Text('main'), GameStates.interruption)
async def handle_interruption_confirmation(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    user_data = await state.get_data()
    with suppress(TelegramBadRequest):
        if 'interrupting_message_id' in user_data:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=user_data['interrupting_message_id'])
        if 'new_message_id' in user_data:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=user_data['new_message_id'])
    if 'pinned_message_id' in user_data:
        await bot.unpin_chat_message(chat_id=callback.message.chat.id, message_id=user_data['pinned_message_id'])
    if 'backup_state' in user_data and user_data['backup_state'] == GameStates.answer:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API}/finish',
                json={
                    'round_id': user_data['round_id'],
                    'abort': True
                }
            ):
                logger.info(f'GAME Aborted round {user_data["round_id"]} by {format_player(user_data["player"])}')
        await state.set_data({'player': user_data['player'], 'round_is_finished': True})
        await handle_command_start(message=callback.message, state=state, bot=bot, callback=callback)
        return
    # await state.set_data({'player': user_data['player']})
    await state.set_data({})
    await handle_command_start(message=callback.message, state=state, bot=bot, callback=callback)


@game_router.callback_query(Text('go_on'), GameStates.interruption)
async def handle_interruption_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = await state.get_data()
    await callback.message.delete()
    await callback.answer()
    await user_data['interrupting_message'].delete()
    await state.set_state(user_data['backup_state'])


@game_router.callback_query(Text('main'))
async def handle_query_main(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    user_data = await state.get_data()
    after_results = False
    if 'round_is_finished' in user_data and user_data['round_is_finished']:
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


@game_router.callback_query(Text('rating'), GameStates.main)
async def handle_query_rating(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = await state.get_data()
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'{API}/rating'
        ) as response:
            if response.status != 200:
                decoded_response = await response.json()
                await handle_error_response(callback, state, decoded_response['detail'])
                logger.warning(f'GAME Getting rating: {decoded_response["detail"]}')
                return
            top_players = await response.json()
    formatted_rating = await format_rating(top_players, user_data['player'])
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
    if 'round_is_finished' in user_data and user_data['round_is_finished']:
        await state.update_data(round_is_finished=False)
        after_results = True
    if 'challenged_topic_id' in user_data:
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f'{API}/player',
                json={
                    'player_id': user_data['player']['id'],
                    'referrer_id': user_data['referrer_id'],
                }
            ) as response:
                pass
            async with session.get(
                f'{API}/topic',
                params={
                    'topic_id': user_data['challenged_topic_id'],
                }
            ) as response:
                if response.status == 200:
                    topic = await response.json()
                    await state.update_data(topic_id=user_data['challenged_topic_id'], topic_title=topic['title'])
                    await handle_query_topic(callback, state)
                    logger.info(f'GAME Accepted challenge on {topic["title"]} by {format_player(user_data["player"])}')
                    return
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'{API}/random-topics',
            params={
                'player_id': user_data['player']['id'],
            }
        ) as response:
            if response.status != 200:
                decoded_response = await response.json()
                await handle_error_response(callback, state, decoded_response['detail'])
                logger.warning(f'GAME Getting random topics by {format_player(user_data["player"])}: '
                               f'{decoded_response["detail"]}')
                return
            topics = await response.json()
    await state.update_data(topics={topic['id']: topic['title'] for topic in topics})
    buttons = [[(topic['title'], f'id{topic["id"]}')] for topic in topics]
    buttons.append(['main'])
    new_message = await callback.message.answer(
        Messages.choose_topic,
        reply_markup=await get_keyboard(buttons)
    )
    await state.update_data(new_message_id=new_message.message_id)
    if after_results:
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.message.delete()
    await callback.answer()
    await state.set_state(GameStates.topic)


@game_router.callback_query(Text(startswith='id'), GameStates.topic)
async def handle_query_topic(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = await state.get_data()
    if 'topic_id' not in user_data:
        topic_id = int(callback.data.replace('id', ''))
        topic_title = user_data['topics'][str(topic_id)]  # no json deserialization from redis
        await state.update_data(topic_id=topic_id, topic_title=topic_title)
    else:
        topic_id = user_data['topic_id']
        topic_title = user_data['topic_title']
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{API}/round',
            json={
                'player_id': user_data['player']['id'],
                'topic_id': topic_id
            }
        ) as response:
            decoded_response = await response.json()
            if response.status == 200:
                logger.info(f'GAME Started round {decoded_response["id"]} by {format_player(user_data["player"])} '
                            f'on {topic_title}')
            else:
                await state.update_data(challenged_topic_id=None, referrer_id=None)
                await handle_error_response(callback, state, decoded_response['detail'])
                logger.warning(f'GAME Starting round by {format_player(user_data["player"])} on {topic_title}: '
                               f'{decoded_response["detail"]}')
                return
            round = await response.json()
            await state.update_data(round_id=round['id'], hits=[], score1=0, score2=0)
    pinned_message = await callback.message.answer(f'Тема: {topic_title}')
    await pinned_message.pin(disable_notification=True)
    await state.update_data(pinned_message_id=pinned_message.message_id)
    new_message = await callback.message.answer(Messages.left5)
    await state.update_data(new_message_id=new_message.message_id)
    await callback.message.delete()
    await callback.answer()
    await state.set_state(GameStates.answer)


@game_router.message(F.text, GameStates.answer)
async def handle_message_answer(message: Message, state: FSMContext, bot: Bot) -> None:
    user_data = await state.get_data()
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{API}/answer',
            json={
                'round_id': user_data['round_id'],
                'answer': message.text
            }
        ) as response:
            if response.status == 200:
                logger.info(f'GAME Sent answer "{message.text}" by {format_player(user_data["player"])} '
                            f'at round {user_data["round_id"]}')
            else:
                decoded_response = await response.json()
                await message.answer(decoded_response['detail'])
                logger.warning(f'GAME Sending answer "{message.text}" by {format_player(user_data["player"])} '
                               f'at round {user_data["round_id"]}: {decoded_response["detail"]}')
                return
            result = await response.json()
    if result['entities'] and len(result['entities']) > 1:
        await state.update_data(ambiguous_answer=message.text)
        buttons = [[(entity['title'], f'id{entity["id"]}')] for entity in result['entities']]
        await message.answer(
            Messages.ambiguity,
            reply_markup=await get_keyboard(buttons)
        )
        return
    if result['entities']:
        entity = result['entities'][0]
        if entity['points']:
            await message.answer(choice(Messages.hit))
            await handle_hit(message, state, entity, bot=bot)
        else:
            await message.answer(Messages.miss)
    elif not result['skipped']:
        await message.answer(Messages.miss)
    await handle_bot_answer(message, state, bot, result)


@game_router.callback_query(Text(startswith='id'), GameStates.answer)
async def handle_query_answer(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    user_data = await state.get_data()
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{API}/answer',
            json={
                'round_id': user_data['round_id'],
                'answer': user_data['ambiguous_answer'],
                'entity_id': int(callback.data.replace('id', ''))
            }
        ) as response:
            if response.status == 200:
                logger.info(f'GAME Specified answer "{user_data["ambiguous_answer"]}" '
                            f'by {format_player(user_data["player"])} at round {user_data["round_id"]}')
            else:
                decoded_response = await response.json()
                await callback.message.answer(decoded_response['detail'])
                await callback.message.delete()
                await callback.answer()
                logger.warning(f'GAME Specifying answer "{user_data["ambiguous_answer"]}" '
                               f'by {format_player(user_data["player"])} at round {user_data["round_id"]}: '
                               f'{decoded_response["detail"]}')
                return
            result = await response.json()
            entity = result['entities'][0]
    await handle_hit(callback.message, state, entity, bot=bot)
    await handle_bot_answer(callback.message, state, bot, result)
    await callback.message.delete()
    await callback.answer()


async def handle_bot_answer(message: Message, state: FSMContext, bot: Bot, result: dict) -> None:
    bot_answer = Messages.bot_answer.replace('ANSWER', result['bot_answer'])
    if result['bot_answer_entity']['position'] > 10:
        bot_answer += Messages.bot_miss
    await bot.send_chat_action(message.chat.id, 'typing')
    await asyncio.sleep(randint(1, 3))
    await message.answer(bot_answer)
    await asyncio.sleep(2)
    await handle_hit(message, state, result['bot_answer_entity'], from_bot=True, bot=bot)
    attempts_left_message = getattr(Messages, f'left{result["attempts_left"]}')
    new_message = await message.answer(attempts_left_message)
    await state.update_data(new_message_id=new_message.message_id)
    if not result['attempts_left']:
        await handle_results(message, state, bot)


async def handle_hit(
        message: Message,
        state: FSMContext,
        entity: dict,
        from_bot: bool = False,
        bot: Bot = None
) -> None:
    user_data = await state.get_data()
    score1, score2 = user_data['score1'], user_data['score2']
    hit_record = {
        'position': entity['position'],
        'answer': entity['title'],
        'points': entity['points'],
        'player': 2 if from_bot else 1
    }
    hits = user_data['hits']
    if hit_record['points']:
        hits.append(hit_record)
        await state.update_data(hits=hits)
    if not from_bot:
        if hit_record['points']:
            await state.update_data(last_hit_position=hit_record['position'])
            score1 = score1 + hit_record['points']
            await state.update_data(score1=score1)
        return
    last_hit_positions = []
    if hit_record['points']:
        last_hit_positions.append(hit_record['position'])
        score2 = score2 + hit_record['points']
        await state.update_data(score2=score2)
    if 'last_hit_position' in user_data and user_data['last_hit_position']:
        last_hit_positions.append(user_data['last_hit_position'])
    await state.update_data(last_hit_position=None)
    new_message = await message.answer(await format_hits(hits, last_hit_positions=last_hit_positions))
    await state.update_data(new_message_id=new_message.message_id)
    with suppress(TelegramBadRequest):
        await bot.edit_message_text(
            text=html.bold(f'{score1}:{score2} | {user_data["topic_title"]}'),
            chat_id=message.chat.id,
            message_id=user_data['pinned_message_id']
        )


async def handle_results(message: Message, state: FSMContext, bot: Bot) -> None:
    user_data = await state.get_data()
    referral = await encode_referral(user_data['topic_id'], user_data['player']['id'])
    score1, score2 = user_data['score1'], user_data['score2']
    outcome = f'{score1}:{score2}'
    if score1 == score2:
        outcome_message = Messages.outcome_draw.replace('RESULT', outcome)
    elif score1 > score2:
        outcome_message = Messages.outcome_victory.replace('RESULT', outcome)
    else:
        outcome_message = Messages.outcome_defeat.replace('RESULT', outcome)
    challenge_message = Messages.challenge.replace('TOPIC', user_data['topic_title']).replace('RESULT', outcome_message)
    deeplink = f'https://t.me/NiceTryGameBot?start={referral}'
    formatted_results = await format_hits(user_data['hits'])
    await bot.unpin_chat_message(chat_id=message.chat.id, message_id=user_data['pinned_message_id'])
    await bot.send_chat_action(message.chat.id, 'typing')
    await asyncio.sleep(3)
    await message.answer_photo(
        Images.results,
        f'{outcome_message}\n\n{formatted_results}',
        reply_markup=await get_keyboard(
            [['main', 'game_again'], ['feedback', 'challenge']],
            deeplink=deeplink,
            challenge_message=challenge_message
        )
    )
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'{API}/finish',
            json={
                'round_id': user_data['round_id'],
                'score1': score1,
                'score2': score2
            }
        ):
            logger.info(f'GAME Finished round {user_data["round_id"]} with {outcome}')
    await state.set_data({
        'player': user_data['player'],
        'round_id': user_data['round_id'],
        'round_is_finished': True,
        'deeplink': deeplink,
        'challenge_message': challenge_message
    })
    await state.set_state(GameStates.main)


@game_router.callback_query(Text('feedback'))
async def handle_feedback(callback: CallbackQuery, state: FSMContext) -> None:
    new_message = await callback.message.answer(Messages.feedback)
    await state.update_data(new_message_id=new_message.message_id)
    await callback.message.delete()
    await callback.answer()
    await state.set_state(GameStates.feedback)


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
        ):
            logger.info(f'GAME Sent feedback "{message.text}" by {format_player(user_data["player"])} '
                        f'at round {user_data["round_id"]}')
    await message.answer(
        Messages.feedback_thanks,
        reply_markup=await get_keyboard(
            [['main', 'challenge']],
            deeplink=user_data['deeplink'],
            challenge_message=user_data['challenge_message']
        )
    )
    await state.set_state(GameStates.main)


@game_router.message(F.text)
async def handle_any_message(message: Message, state: FSMContext) -> None:
    await handle_default(message, state)


@game_router.callback_query()
async def handle_any_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await handle_default(callback.message, state)


async def handle_default(message: Message, state: FSMContext) -> None:
    await message.answer(Messages.default)


async def handle_error_response(callback: CallbackQuery, state: FSMContext, error_message: str) -> None:
    await callback.message.answer(
        error_message,
        reply_markup=await get_keyboard([['main']])
    )
    await callback.message.delete()
    await callback.answer()
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
