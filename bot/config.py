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
LOG_FILE = env.str('LOG_FILE', '/var/log/bot/debug.log')


# TODO duel rules
class Messages():
    ambiguity = 'Какой ответ вы имели в виду?'
    attempt1 = 'У вас есть 5 попыток, чтобы угадать самые популярные ответы этой темы. Начинайте:'
    attempt2 = 'У вас есть 5 попыток, чтобы угадать самые популярные ответы этой темы. Начинайте:'
    attempt3 = 'Что ещё знаете по этой теме? У вас 4 попытки'
    attempt4 = 'Что ещё знаете по этой теме? У вас 4 попытки'
    attempt5 = 'Какова ваша следующая версия? Осталось 3 попытки. Чтобы пропустить любой ход, отправьте «-»'
    attempt6 = 'Какова ваша следующая версия? Осталось 3 попытки. Чтобы пропустить любой ход, отправьте «-»'
    attempt7 = 'Осталось 2 попытки. Придумайте ещё что-нибудь'
    attempt8 = 'Осталось 2 попытки. Придумайте ещё что-нибудь'
    attempt9 = 'Последняя попытка. Ваш ответ?'
    attempt10 = 'Последняя попытка. Ваш ответ?'
    attempt11 = 'Все ответы приняты!'
    challenge = dedent('''\
        Приглашаю сыграть тему «TOPIC» в игре GuessTop против ChatGPT.
        RESULT. Сможешь улучшить?
        Перейди по ссылке и нажми кнопку START''')
    chatgpt_answer = 'Ответ ChatGPT: ANSWER'
    choose_duel_mode = dedent('''\
        Соперник выбрал тему: TOPIC.
        Выберите режим игры.
        Очки: Побеждает тот, кто наберёт больше очков после 5 попыток.
        Попадания: Побеждает тот, кто первым наберёт 3 попадания в десятку.''')
    choose_duel_topic1 = dedent('''\
        Для дуэли предлагаются темы: TOPICS.
        Уберите тему, которая вам НЕ нравится.
        После этого соперник сделает свой выбор.''')
    choose_duel_topic2 = dedent('''\
        Выберите одну из тем: TOPICS.
        После этого соперник выберет режим игры.''')
    choose_mode = dedent('''\
        Выберите режим игры.
        Очки: Побеждает тот, кто наберёт больше очков после 5 попыток.
        Попадания: Побеждает тот, кто первым наберёт 3 попадания в десятку.''')
    choose_topic = 'Выберите одну из тем: TOPICS'
    closed = dedent('''\
        Игра временно не работает.
        Андрей фиксит баги и внедряет новые фичи.
        Отправим сообщение, когда всё наладится''')
    confirm_interruption = 'Действительно хотите прервать текущий раунд?'
    create_duel = dedent('''\
        Вы можете создать дуэль и подождать, пока на вызов ответит человек, либо играть сразу против ChatGPT''')
    default = 'Что-то пошло не так? Для выхода в главное меню нажмите /start'
    duel_call = 'DUELIST ожидает соперника. Хотите сыграть против него?'
    duel_opponent_waiting = 'Ожидаем ход соперника'
    duel_start_waiting = 'Ожидайте, когда появится соперник и примет вызов'
    feedback = 'Напишите в свободной форме о любой встреченной ошибке либо свои замечания и предложения'
    feedback_thanks = 'Спасибо! Постараемся ответить в ближайшее время'
    hit = ('Отличный ход!', 'Есть контакт!', 'Такой ответ есть в десятке!', 'Хорошая попытка!', 'Точно в цель!')
    hits_mode_attempt = (
        'Придумайте ещё что-нибудь', 'Что ещё знаете по этой теме?', 'Следующая версия:', 'Продолжаем играть:'
    )
    hits_mode_chosen = 'Соперник выбрал режим игры «Попадания»'
    hits_mode_first = 'Вам нужно угадать 3 ответа из десятки самых популярных быстрее соперника. Начинайте:'
    hits_mode_second = 'Какова ваша следующая версия? Чтобы пропустить любой ход, отправьте «-»'
    invite = dedent('''\
        Приглашаю сыграть в игру NiceTry против меня или ChatGPT.
        Перейди по ссылке и нажми кнопку START''')
    miss = 'Этот ответ не входит в десятку популярных'
    miss_addition = ' (он не попал в десятку)'
    open = 'Игра снова работает'
    opponent_answer = 'Ответ соперника: ANSWER'
    opponent_skipped = 'Соперник пропустил ход'
    outcome_defeat = 'Итоговый счёт — RESULT в пользу ChatGPT'
    outcome_draw = 'Итоговый счёт — RESULT'
    outcome_player1 = 'Итоговый счёт — RESULT в пользу PLAYER1'
    outcome_player2 = 'Итоговый счёт — RESULT в пользу PLAYER2'
    outcome_victory = 'Итоговый счёт — RESULT в вашу пользу'
    points_mode_chosen = 'Соперник выбрал режим игры «Очки»'
    rating_change = 'Ваш рейтинг: RATING, место: POSITION'
    rating_formula = dedent('''\
        Рейтинг рассчитывается по формуле:
            О + П×40 + Н×20, где:
        О — сумма очков в последних 10  партиях,
        П — количество побед в последних 10 партиях,
        Н — количество ничьих в последних 10 партиях.
        ———————————————————————————
        Рейтинг подвержен старению.
        Партии текущего дня учитываются в полном объёме.
        Чем больше дней тому назад сыграна партия, тем сильнее понижающий коэффициент.''')
    rules = dedent('''\
        🔹 Вам нужно называть ассоциации на выбранную тему.
        🔹 Чем чаще другие люди дают такой же ответ, тем больше очков вы получаете.
        🔹 За самый популярный ответ можно заработать 10 очков и далее по убыванию.
        🔹 В режиме игры на очки у вас с соперником по 5 попыток, побеждает набравший больше очков.
        🔹 В режиме игры на попадания выигрывает тот, кто быстрее угадает 3 попадания в десятку.
        🔹 Игра распознаёт разные варианты написаний реалий и даже прощает небольшие опечатки.''')
    start_again = 'Нажмите ещё раз /start'
    welcome = 'Добро пожаловать в игру NiceTry!'

    class Buttons:
        call_duel = '👤 Принять вызов человека'
        cancel_duel = '❌ Отменить дуэль'
        chatgpt = '🤖 Играть против ChatGPT'
        create_duel = '👤 Создать дуэль'
        feedback = '💬 Обратная связь'
        game = '🚀 Играть'
        game_again = '🚀 Играть снова'
        go_on = '🚀 Продолжить игру'
        invite = '😊 Пригласить друга'
        main = '🏠 На главную'
        modehits = '🎯 Попадания'
        modepoints = '⭐ Очки'
        rules = '📜 Правила'
        rating = '🏆 Рейтинг'

    class Emojis:
        chatgpt = '🤖'
        human = '👤'
        new = '✨'
        digits = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        avatars = ['🐵', '🦍', '🦧', '🐶', '🐺', '🦊', '🦝', '🐱', '🦁', '🐯', '🐆', '🐴', '🦄', '🦓', '🦌'] +\
                  ['🐪', '🦙', '🦒', '🦣', '🐘', '🦏', '🦛', '🐮', '🐷', '🐏', '🐐', '🐭', '🐹', '🐰', '🐿️'] +\
                  ['🦫', '🦔', '🦇', '🐻', '🐻‍❄️', '🐨', '🐼', '🦥', '🦦', '🦨', '🦘', '🐔', '🐓', '🐤', '🐦'] +\
                  ['🐧', '🕊️', '🦅', '🦆', '🦢', '🦉', '🦤', '🦩', '🦜', '🐸', '🐊', '🐢', '🦎', '🐍', '🐲'] +\
                  ['🦕', '🦖', '🐟', '🐋', '🐬', '🦭', '🐠', '🐡', '🦈', '🐙', '🐌', '🦋', '🐜', '🐝', '🪲'] +\
                  ['🐞', '🦂', '🪰']


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
