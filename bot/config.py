from textwrap import dedent

from environs import Env

env = Env()
env.read_env()

ADMIN_ID = env.int('ADMIN_ID')
API = env('API')
TG_TOKEN = env('TG_TOKEN')
LOGO_URL = 'https://lh3.googleusercontent.com/drive-viewer/AFGJ81rjGM-HN9T1IGotrw0PpjcQ-9qJGuK5tpjmCNSP5VMUovhR_zrqyuuZkekF1_xgQGkJ_d7YNLqQNJAweCzAsEniQdbd=s1600'  # noqa
OPEN = env.bool('OPEN')
DEV_BOT = env.bool('DEV_BOT')


class Messages():
    ambiguity = 'Какой ответ вы имели в виду?'
    bot_answer = 'Ответ соперника: ANSWER'
    bot_miss = ' (он не попал в десятку)'
    challenge = dedent('''\
        Приглашаю сыграть тему «TOPIC» в игре GuessTop против ChatGPT.
        RESULT. Сможешь улучшить?
        Перейди по ссылке и нажми кнопку START''')
    choose_mode = dedent('''\
        Выберите режим игры.
        Очки: Побеждает тот, кто наберёт больше очков после 5 попыток.
        Попадания: Побеждает тот, кто первым наберёт 3 попадания в десятку.''')
    choose_topic = 'Выберите одну из трёх тем: '
    closed = dedent('''\
        Игра временно не работает.
        Андрей фиксит баги и внедряет новые фичи.
        Отправим сообщение, когда всё наладится''')
    confirm_interruption = 'Действительно хотите прервать текущий раунд?'
    default = 'Что-то пошло не так? Для выхода в главное меню нажмите /start'
    feedback = 'Напишите в свободной форме о любой встреченной ошибке либо свои замечания и предложения'
    feedback_thanks = 'Спасибо! Постараемся ответить в ближайшее время'
    hit = ('Вы угадали!', 'Есть контакт!', 'Такой ответ есть в десятке!', 'Хорошая попытка!', 'Точно в цель!')
    hits_mode_attempt = (
        'Придумайте ещё что-нибудь', 'Что ещё знаете по этой теме?', 'Следующая версия:', 'Продолжаем играть:'
    )
    hits_mode_first = 'Вам нужно угадать 3 ответа из десятки самых популярных быстрее соперника. Начинайте:'
    hits_mode_second = 'Какова ваша следующая версия? Чтобы пропустить любой ход, отправьте «-»'
    attempt1 = 'У вас есть 5 попыток, чтобы угадать самые популярные ответы этой темы. Начинайте:'
    attempt2 = 'Что ещё знаете по этой теме? У вас 4 попытки'
    attempt3 = 'Какова ваша следующая версия? Осталось 3 попытки. Чтобы пропустить любой ход, отправьте «-»'
    attempt4 = 'Осталось 2 попытки. Придумайте ещё что-нибудь'
    attempt5 = 'Последняя попытка. Ваш ответ?'
    attempt6 = 'Все ответы приняты!'
    miss = 'Этот ответ не входит в десятку популярных'
    open = 'Игра снова работает'
    outcome_defeat = 'Итоговый счёт — RESULT в пользу ChatGPT'
    outcome_draw = 'Итоговый счёт — RESULT'
    outcome_victory = 'Итоговый счёт — RESULT в вашу пользу'
    rating_formula = dedent('''\
        Рейтинг рассчитывается по формуле: О + П×40 + Н×20, где:
        О — сумма очков в последних 10  партиях,
        П — количество побед в последних 10 партиях,
        Н — количество ничьих в последних 10 партиях''')
    rules = dedent('''\
        🔹 Вам нужно называть ассоциации на выбранную тему.
        🔹 Чем чаще другие люди дают такой же ответ, чем больше очков вы зарабатываете.
        🔹 За самый популярный ответ можно заработать 10 очков и далее по убыванию.
        🔹 В каждом раунде у вас с соперником по 5 попыток.
        🔹 Игра распознаёт разные варианты написаний реалий и даже прощает небольшие опечатки.''')
    start_again = 'Нажмите ещё раз /start'
    welcome = 'Добро пожаловать в игру NiceTry!'

    class Buttons:
        main = '🏠 На главную'
        game = '🚀 Играть'
        game_again = '🚀 Играть снова'
        rules = '📜 Правила'
        rating = '🏆 Рейтинг'
        points_mode = '⭐ Очки'
        hits_mode = '🎯 Попадания'
        challenge = '⚔️ Вызвать друга'
        go_on = '🚀 Продолжить игру'
        feedback = '💬 Обратная связь'

    class Emojis:
        bot = '🤖'
        human = '👤'
        new = '✨'
        num1 = '1️⃣'
        num2 = '2️⃣'
        num3 = '3️⃣'
        num4 = '4️⃣'
        num5 = '5️⃣'
        num6 = '6️⃣'
        num7 = '7️⃣'
        num8 = '8️⃣'
        num9 = '9️⃣'
        num10 = '🔟'


class Images():
    main = 'AgACAgIAAxkDAAMOZGDnb8Bt8_PDKgrVRQT-435IxAoAAmnHMRt8fAFLEZ74YiwFtJIBAAMCAAN5AAMvBA'
    rating = 'AgACAgIAAxkDAAMPZGDnb89EZau-81uGZZBuU6gb30gAAmrHMRt8fAFLTQ0WmYjaMeUBAAMCAAN5AAMvBA'
    results = 'AgACAgIAAxkDAAMQZGDncKIAAeQvXK4E1PkYRTvRQA4KAAJrxzEbfHwBS_dYvIRp1cYPAQADAgADeQADLwQ'
    rules = 'AgACAgIAAxkDAAMRZGDncCMbdbefqwsXQJM7OyequQIAAmzHMRt8fAFLM5OPz8PapL0BAAMCAAN5AAMvBA'


if DEV_BOT:
    white = 'https://bourayne-preissl.com/wp-content/uploads/2016/03/Reticular-Tissue-White-Seamless-Texture.jpg'
    Images.main = white
    Images.rating = white
    Images.results = white
    Images.rules = white
