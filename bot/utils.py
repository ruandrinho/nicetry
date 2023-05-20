from urllib.parse import urlencode

from aiogram import html
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from texttable import Texttable

from config import Messages

BASE52 = 'yQAIVhTKcLMtJjWXzPuwCSpqsrmfEanNBFHUivxbRkOoGYdZelDg'


async def decimal_to_base52(decimal: int, result: str = '') -> str:
    if decimal == 0:
        return result[::-1]
    remainder = decimal % 52
    result += BASE52[remainder]
    return await decimal_to_base52(decimal // 52, result)


async def base52_to_decimal(s: str, index: int = 0) -> int:
    if index == len(s):
        return 0
    digit = s[-(index + 1)]
    value = BASE52.index(digit)
    return (52 ** index) * value + await base52_to_decimal(s, index + 1)


async def encode_referral(topic_id: int, player_id: int) -> str:
    return f'{await decimal_to_base52(topic_id)}-{await decimal_to_base52(player_id)}'


async def decode_referral(s: str) -> list[int]:
    s1, s2 = s.split('-')
    return [await base52_to_decimal(s1), await base52_to_decimal(s2)]


def format_player(player: dict) -> str:
    return f'{player["displayed_name"]} id {player["id"]}'


async def get_button(button: str | tuple[str], **kwargs) -> InlineKeyboardButton:
    if button == 'challenge':
        url_params = urlencode({'url': kwargs['deeplink'], 'text': kwargs['challenge_message']})
        url = f'https://t.me/share/url?{url_params}'
        return InlineKeyboardButton(text=getattr(Messages.Buttons, button), url=url)
    elif type(button) == str:
        return InlineKeyboardButton(text=getattr(Messages.Buttons, button), callback_data=button)
    elif type(button) == tuple:
        text, callback_data = button
        return InlineKeyboardButton(text=text, callback_data=callback_data)


async def get_keyboard(layout: list[list[str | tuple[str]]], **kwargs) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[await get_button(button, **kwargs) for button in row] for row in layout]
    )


async def format_rating(top_players: list[dict], current_player: dict) -> str:
    table = Texttable()
    table.set_max_width(25)
    table.set_deco(Texttable.HEADER)
    table.set_chars(['-', '|', '+', '-'])
    table.set_cols_width([20, 4])
    table.set_cols_align(['l', 'l'])
    table.set_header_align(['l', 'l'])
    table.add_rows([['Игрок', 'Очки']])
    for position, player in enumerate(top_players, start=1):
        table.add_row([f'{position}. {player["displayed_name"]}', player['rating']])
    if current_player not in top_players:
        table.add_row(['', ''])
        table.add_row(
            [f'{current_player["position"]}. {current_player["displayed_name"]}', current_player['rating']]
        )
    return html.pre(html.quote(table.draw()))


async def format_hits(hits: list[dict], last_hit_positions: list[int] = []) -> str:
    hits = sorted(hits, key=lambda hit: hit['position'])
    table = Texttable()
    table.set_max_width(25)
    table.set_deco(Texttable.HEADER | Texttable.HLINES)
    table.set_chars(['-', '|', '+', '-'])
    table.set_cols_width([1, 18, 4])
    table.set_cols_align(['l', 'l', 'l'])
    table.set_header_align(['l', 'l', 'l'])
    table.add_rows([['', 'Место и ответ', 'Очки']])
    for hit in hits:
        if hit['position'] in last_hit_positions:
            hit['answer'] = f'{Messages.Emojis.new} {hit["answer"]}'
        hit['player'] = Messages.Emojis.human if hit['player'] == 1 else Messages.Emojis.bot
        hit['points'] = getattr(Messages.Emojis, f'num{hit["points"]}')
        table.add_row([hit['player'], f'{hit["position"]}. {hit["answer"]}', hit['points']])
    return html.pre(html.quote(table.draw()))
