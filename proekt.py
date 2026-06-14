import telebot
import os
from dotenv import load_dotenv
# Загружаем переменные из файла .env
load_dotenv()
import schedule
import pytz
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from aiosmtplib import SMTP
import threading
import asyncio
import time
from gtts import gTTS
import os
import random

API_TOKEN = os.getenv("BOT_API_TOKEN")
CHAT_ID = os.getenv("BOT_CHAT_ID")
EMAIL = os.getenv("BOT_EMAIL")
PWD = os.getenv("BOT_PASSWORD")

# Проверка, чтобы сразу видеть, если что-то забыли
# Проверка, чтобы сразу видеть, если что-то забыли
if not all([API_TOKEN, CHAT_ID, EMAIL, PWD]):
    missing = [k for k, v in {"BOT_API_TOKEN": API_TOKEN, "BOT_CHAT_ID": CHAT_ID, "BOT_EMAIL": EMAIL, "BOT_PASSWORD": PWD}.items() if not v]
    raise ValueError(f"Не заданы переменные окружения: {', '.join(missing)}. Проверь файл .env")

bot = telebot.TeleBot(API_TOKEN)

moscow_tz = pytz.timezone('Europe/Moscow')

def send_message(): 
    bot.send_message(CHAT_ID, "Не забудь о домашнем задании по физике!")

schedule.every().monday.at("15:30").do(send_message)

def run_schedule():
    while True:
        moscow_time = datetime.now(moscow_tz)
        current_time_str = moscow_time.strftime("%H:%M")
        if current_time_str == "15:30":
            schedule.run_pending()
        time.sleep(1)

threading.Thread(target=run_schedule).start()

@bot.message_handler(commands=['plan'])
def start(message):
    bot.send_message(message.chat.id,  "Бот напомнит Вам о задании по физике по понедельникам в 15:30 по Москве!")

async def send_mail(subject, to, msg):
    message = MIMEMultipart()
    message["From"] = EMAIL
    message["To"] = to
    message["Subject"] = subject
    message.attach(MIMEText(
        f"<html><body>{msg}</body></html>",
        "html",
        "utf-8"
    ))

    try:
        smtp_client = SMTP(hostname="smtp.yandex.ru", port=465, use_tls=True)
        async with smtp_client:
            await smtp_client.login(EMAIL, PWD)
            await smtp_client.send_message(message)
    except Exception as e:
        print(f'Ошибка отправки письма: {e}')

# Словарь для хранения данных пользователей (включая ответы на тест)
user_data = {}

# Словарь терминов с их определениями
TERMINS = {
    'скорость': 'Физическая величина, которая характеризует быстроту изменения положения тела в пространстве относительно выбранной системы отсчёта. Она показывает, какое расстояние преодолевает объект за единицу времени.',
    'ускорение': 'Физическая величина, которая характеризует быстроту изменения скорости тела. Она показывает, насколько изменяется скорость тела за единицу времени.',
    'сила': 'Векторная физическая величина, мера воздействия на материальную точку (тело) со стороны других тел.'
}

asyncio_loop = None

def start_asyncio_loop():
    global asyncio_loop
    asyncio_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(asyncio_loop)
    asyncio_loop.run_forever()

async def send_async_message(chat_id):
    try:
        await asyncio.sleep(5)
        bot.send_message(
            chat_id,
            "<u>Пробные варианты ОГЭ можно пройти на сайте:</u>\n"
            '<a href="https://phys-oge.sdamgia.ru/sprav">ОГЭ-2026</a>\n',
            parse_mode='HTML'
        )
    except Exception as e:
        print(f'Ошибка при отправке сообщения {e}')

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Здравствуйте!\nЯ <b>Бот</b>, который поможет <i>Пользователю</i>:\n"
        "\n<b>1.</b> Найти необходимое <i>определение</i> курса физики;\n"
        "<b>2.</b> Озвучить его;\n"
        "<b>3.</b> Дать ссылку на дополнительный материал <i>учебника</i>.\n"
        "<b>4.</b> Пройти пробные варианты <i>ОГЭ</i>.\n"
        "<b>5.</b> Напомнить о <i>домашнем задании</i> по физике.\n"
        "\n<i>Для начала работы необходимо ввести команду — <b>/termin</b>!</i>\n"
        "<i>Для проверки</i> своих знаний по изученному материалу необходимо ввести команду — <b>/test</b>!\n"
        "Для напоминания о <i>домашнем задании</i> необходимо ввести команду — <b>/plan</b>!\n",
        parse_mode='HTML'
    )

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(
        "Виртуальные лабораторные работы",
        url="https://www.lektorium.tv/physics"
    ))
    bot.send_message(
        message.chat.id,
        "Дополнительные материалы:",
        reply_markup=markup
    )

    if asyncio_loop and asyncio_loop.is_running():
        asyncio.run_coroutine_threadsafe(send_async_message(message.chat.id), asyncio_loop)

# Запускаем asyncio loop в отдельном потоке ДО вызова bot.polling()
asyncio_thread = threading.Thread(target=start_asyncio_loop, daemon=True)
asyncio_thread.start()
time.sleep(1)

@bot.message_handler(commands=['termin'])
def change_termin(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add('Скорость', 'Ускорение', 'Сила')
    msg = bot.reply_to(message, "Выберите термин", reply_markup=markup)
    bot.register_next_step_handler(message, set_termin_and_speak)

def set_termin_and_speak(message):
    user_input = message.text.strip().lower()
    if user_input in TERMINS:
        definition = TERMINS[user_input]
        try:
            tts = gTTS(text=definition, lang='ru')
            tts.save('audio.mp3')
            with open('audio.mp3', 'rb') as audio:
                bot.send_audio(message.chat.id, audio)
        except Exception as e:
            bot.reply_to(message, 'Произошла ошибка при озвучке текста.')
            print(f'Ошибка: {e}')
        finally:
            if os.path.exists('audio.mp3'):
                os.remove('audio.mp3')
    else:
        bot.reply_to(message, "Извините, это понятие ещё не введено в учебник, но Вы можете найти его на сайте: https://ru.ruwiki.ru/wiki/Базовые_физические_понятия")

@bot.message_handler(commands=['test'])
def start_test(message):
    term, definition = random.choice(list(TERMINS.items()))
    user_data[message.chat.id] = {'correct_answer': term}

    markup = telebot.types.InlineKeyboardMarkup()
    buttons = [
        telebot.types.InlineKeyboardButton(t, callback_data=f"test_{t.lower()}")
        for t in TERMINS.keys()
    ]
    for b in buttons:
        markup.add(b)

    bot.send_message(
        message.chat.id,
        f"Выберите верный термин:\n\n<i>{definition}</i>",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('test_'))
def check_answer_inline(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "Тест нужно начать заново командой /test", show_alert=True)
        return

    correct_answer = user_data[chat_id]['correct_answer']
    user_answer = call.data[5:].lower()  
    correct_answer_lower = correct_answer.lower()

    is_correct = user_answer == correct_answer_lower

    if is_correct:
        response = "Ответ верный!"
        photo_url = 'https://www.vecteezy.com/vector-art/14830409-kids-sport-winners-standing-on-podium.jpg'
        bot.send_photo(chat_id, photo=photo_url)
    else:
        response = (
            f"Вы ошиблись. Правильный ответ: <b>{correct_answer.capitalize()}</b>.\n"
            "Обратитесь к учебнику: https://sh2-neman-r27.gosweb.gosuslugi.ru/netcat_files/30/50/Fizika_7_klass.pdf"
        )

    # Пытаемся отредактировать сообщение; если нельзя — отправляем новое
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=response,
            parse_mode='HTML'
        )
    except Exception:
        # Если редактировать нельзя, отправляем как новое сообщение
        bot.send_message(chat_id, response, parse_mode='HTML')

    if asyncio_loop and asyncio_loop.is_running():
        status_text = "верно" if is_correct else "ошибка"
        asyncio.run_coroutine_threadsafe(
            send_mail(
                'Результат теста по физике',
                EMAIL,
                f'<h1>Результат теста: {status_text}</h1>'
                f'<p>Ваш ответ: {user_answer}</p>'
                f'<p>Правильный ответ: {correct_answer}</p>'
            ),
            asyncio_loop
        )

    del user_data[chat_id]
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'):
        return
    bot.reply_to(message, "Извините, это понятие ещё не введено в учебник, но Вы можете найти его на сайте: https://www.lektorium.tv/physics")


if __name__ == "__main__":
    try:
        # Сначала запускаем фоновый поток с расписанием
        threading.Thread(target=run_schedule, daemon=True).start()
        print("Планировщик задач запущен.")
        
        # Потом запускаем бота
        print("Бот запущен. Ожидание сообщений...")
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        print("\nОстановка по Ctrl+C (пользователь прервал выполнение).")
    except Exception as e:
        # Сюда попадёт любая ошибка, если она возникнет ДО или ВО ВРЕМЯ работы
        print(f"\nНЕПРЕДВИДЕННАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()  # покажет точный номер строки с ошибкой
    finally:
        # Этот блок сработает всегда: и при ошибке, и при Ctrl+C
        input("\nНажми Enter для полного выхода из программы...")