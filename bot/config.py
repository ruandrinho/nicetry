from textwrap import dedent

from environs import Env

env = Env()
env.read_env()

API = env('API')
TG_TOKEN = env('TG_TOKEN')
LOGO_URL = 'https://lh3.googleusercontent.com/drive-viewer/AFGJ81rjGM-HN9T1IGotrw0PpjcQ-9qJGuK5tpjmCNSP5VMUovhR_zrqyuuZkekF1_xgQGkJ_d7YNLqQNJAweCzAsEniQdbd=s1600'  # noqa


class Messages():
    ambiguity = 'Какой ответ вы имели в виду?'
    bot_answer = 'Ответ соперника: ANSWER'
    challenge = dedent('''\
        Приглашаю сыграть тему «TOPIC» в игре GuessTop против ChatGPT.
        RESULT. Сможешь улучшить?
        Перейди по ссылке и нажми кнопку START''')
    choose_topic = 'Выберите одну из трёх тем'
    confirm_interruption = 'Действительно хотите прервать текущий раунд?'
    feedback = 'Напишите в свободной форме о любой встреченной ошибке либо свои замечания и предложения'
    feedback_thanks = 'Спасибо! Постараемся ответить в ближайшее время'
    hit = ('Вы угадали!', 'Есть контакт!', 'Такой ответ есть в десятке!', 'Хорошая попытка!', 'Точно в цель!')
    left0 = 'Все ответы приняты!'
    left1 = 'Последняя попытка. Ваш ответ?'
    left2 = 'Осталось 2 попытки. Придумайте ещё что-нибудь'
    left3 = 'Какова ваша следующая версия? Осталось 3 попытки. Чтобы пропустить любой ход, отправьте «-»'
    left4 = 'Что ещё знаете по этой теме? У вас 4 попытки'
    left5 = 'У вас есть 5 попыток, чтобы угадать самые популярные ответы этой темы. Начинайте:'
    miss = 'Этот ответ не входит в десятку популярных'
    outcome_defeat = 'Итоговый счёт — RESULT в пользу ChatGPT'
    outcome_draw = 'Итоговый счёт — RESULT'
    outcome_victory = 'Итоговый счёт — RESULT в вашу пользу'
    rules = dedent('''\
        📌 Вам нужно называть ассоциации на выбранную тему.
        📌 Чем чаще другие люди дают такой же ответ, чем больше очков вы зарабатываете.
        📌 За самый популярный ответ можно заработать 10 очков и далее по убыванию.
        📌 В каждом раунде у вас с соперником по 5 попыток.
        📌 Игра распознаёт разные варианты написаний реалий и даже прощает небольшие опечатки.''')
    welcome = 'Добро пожаловать в игру NiceTry!'

    class Buttons:
        main = '🏠 На главную'
        game = '🚀 Играть'
        rules = '📜 Правила'
        rating = '🏆 Рейтинг'
        challenge = '⚔️ Вызвать друга'
        go_on = '🚀 Продолжить игру'
        feedback = '💬 Обратная связь'


class Images():
    main = 'AgACAgIAAxkDAAMOZGDnb8Bt8_PDKgrVRQT-435IxAoAAmnHMRt8fAFLEZ74YiwFtJIBAAMCAAN5AAMvBA'
    rating = 'AgACAgIAAxkDAAMPZGDnb89EZau-81uGZZBuU6gb30gAAmrHMRt8fAFLTQ0WmYjaMeUBAAMCAAN5AAMvBA'
    results = 'AgACAgIAAxkDAAMQZGDncKIAAeQvXK4E1PkYRTvRQA4KAAJrxzEbfHwBS_dYvIRp1cYPAQADAgADeQADLwQ'
    rules = 'AgACAgIAAxkDAAMRZGDncCMbdbefqwsXQJM7OyequQIAAmzHMRt8fAFLM5OPz8PapL0BAAMCAAN5AAMvBA'
