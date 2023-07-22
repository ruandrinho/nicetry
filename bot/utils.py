from aiogram import html
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from texttable import Texttable

from config import Messages


class Game:
    pass


async def get_button(button: str | tuple[str, str]) -> InlineKeyboardButton:
    if button == 'invite':
        return InlineKeyboardButton(text=getattr(Messages.Buttons, button), url='https://t.me/NiceTryGameBot')
    elif type(button) == str:
        if hasattr(Messages.Buttons, button):
            text = getattr(Messages.Buttons, button)
        else:
            text = getattr(Messages.Buttons, button.split('-')[0])
        return InlineKeyboardButton(text=text, callback_data=button)
    elif type(button) == tuple:
        text, callback_data = button
        return InlineKeyboardButton(text=text, callback_data=callback_data)


async def get_keyboard(layout: list[list[str | tuple[str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[await get_button(button) for button in row] for row in layout]
    )


async def format_rating(top_players: list[dict], current_player: dict) -> str:
    table = Texttable()
    table.set_max_width(25)
    table.set_deco(Texttable.HEADER | Texttable.HLINES)
    table.set_chars(['-', '|', '+', '-'])
    table.set_cols_width([3, 16, 4])
    table.set_cols_align(['r', 'l', 'l'])
    table.set_header_align(['r', 'l', 'l'])
    table.add_rows([['', 'Игрок', 'Очки']])
    for position, player in enumerate(top_players, start=1):
        table.add_row([f'{position}.', player['displayed_name'], player['rating']])
    if current_player not in top_players:
        table.add_row(['...', '...', '...'])
        table.add_row([current_player['position'], current_player['displayed_name'], current_player['rating']])
    return html.pre(html.quote(table.draw()))


# TODO duel
async def format_hits(game_data: dict, results: bool = False) -> str:
    hits = sorted(game_data['hits'], key=lambda hit: hit['position'])
    table = Texttable()
    table.set_max_width(25)
    table.set_deco(Texttable.HEADER | Texttable.HLINES)
    table.set_chars(['-', '|', '+', '-'])
    table.set_cols_width([1, 18, 4])
    table.set_cols_align(['l', 'l', 'l'])
    table.set_header_align(['l', 'l', 'l'])
    table.add_rows([['', 'Место и ответ', 'Очки']])
    for hit in hits:
        if not results and hit == game_data['hits'][-1]:
            hit['answer'] = f'{Messages.Emojis.new} {hit["answer"]}'
        hit['player'] = game_data[f'player{hit["player"]}']['avatar']
        hit['points'] = Messages.Emojis.digits[hit['points'] - 1]
        table.add_row([hit['player'], f'{hit["position"]}. {hit["answer"]}', hit['points']])
    return html.pre(html.quote(table.draw()))


async def format_score(game_data: dict) -> str:
    score_key = 'hits' if game_data['hits_mode'] else 'score'
    score1 = f'{game_data["player1"]["avatar"]} {game_data["player1"][score_key]}'
    score2 = f'{game_data["player2"][score_key]} {game_data["player2"]["avatar"]}'
    return html.bold(
        f'{score1} : {score2} • {game_data["topic"]["title"]}'
    )
