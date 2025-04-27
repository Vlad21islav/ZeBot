import os
import random
import telebot
import requests
import kandinsky
from faster_whisper import WhisperModel

TOKEN = os.environ.get('TOKEN')
weather_api = os.environ.get('weather_api')
news_api = os.environ.get('news_api')
my_id = os.environ.get('my_id')

model = None

if not TOKEN:
    import keys
    TOKEN = keys.TOKEN
    weather_api = keys.weather_api
    news_api = keys.news_api
    my_id = keys.my_id

bot = telebot.TeleBot(TOKEN)


path = ""
# path = "/home/Vlad21islav/ZeBot/"


def get_model():
    global model
    if model is None:
        model = WhisperModel("tiny", compute_type="float32")
    return model


def command_length(message):
    return message.json["entities"][0]["length"]


def add_users(message):
    last_name = f", last_name: {message.from_user.last_name}" if message.from_user.last_name else ""
    nickname = f", nickname: {message.from_user.username}" if message.from_user.username else ""
    name = f", name: {message.from_user.first_name}" if message.from_user.first_name else ""
    user_id = message.from_user.id
    username = f"id: {user_id}{name}{last_name}{nickname}"

    with open(path + "users.txt", "r") as file:
        file = file.read().split("\n")

    ids = []
    for user in file:
        ids.append(user.split(", ")[0])

    if not f"id: {user_id}" in ids:
        with open(path + "users.txt", "a") as file:
            file.write(username + "\n")
        bot.send_message(int(my_id), username)


def main():
    try:
        @bot.message_handler(commands=["start"])
        def start_command(message):
            add_users(message)
            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            btn = telebot.types.InlineKeyboardButton("Показать используемые сервисы", callback_data="show services")
            markup.add(btn)
            bot.send_message(message.chat.id, "Привет, рад тебя видеть! Введи /help для вывода списка команд", reply_markup=markup)

        @bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            if call.data == "show services":
                bot.send_message(call.message.chat.id, f"Для создания бота были использованы такие сервисы как: <b>openweather</b>, <b>kandinsky</b> и <b>newsapi</b>", parse_mode="html")

        @bot.message_handler(commands=["help"])
        def help_command(message):
            add_users(message)
            bot.send_message(message.chat.id, "/help - вывод всех команд\n"
                                              "/weather - вывод погоды в городе в данное время\n"
                                              "/kandinsky - генерация картинок по запросу\n"
                                              "/news - показать текущие новости по теме\n"
                                              "/predict - ответить на вопрос")

        @bot.message_handler(commands=["weather"])
        def get_weather_command(message):
            add_users(message)
            city = message.text.strip()[(command_length(message) + 1):].title()
            res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_api}&units=metric")
            try:
                bot.reply_to(message,
                             f"Погода в городе {city}: \n"
                             f"Температура: {round(res.json()['main']['temp'])}°C\n"
                             f"Ощущается как: {round(res.json()['main']['feels_like'])}°C\n"
                             f"Влажность: {round(res.json()['main']['humidity'])}%")
                bot.send_message(message.chat.id, f"[ㅤ](https://openweathermap.org/img/wn/{res.json()['weather'][0]['icon']}@4x.png)", parse_mode="MarkdownV2")
            except KeyError:
                bot.reply_to(message, f"Город не найден, попробуйте ввести другой")

        @bot.message_handler(commands=["news"])
        def get_news_command(message):
            add_users(message)
            prompt = message.text.strip()[(command_length(message) + 1):].title()

            news_params = {
                'q': 'Россия',  # Запрос по ключевому слову
                'apiKey': news_api,
                'language': 'ru',
            }

            if len(prompt) >= 1:
                news_params["q"] = prompt

            # URL для запроса новостей
            url = 'https://newsapi.org/v2/everything'
            response = requests.get(url, params=news_params)

            if response.status_code == 200:
                data = response.json()

                # Печать заголовков новостей
                text = ""
                max_length = 20
                # Вывод заголовков новостей
                for article in data["articles"]:
                    text += "\n" * 2 + article["title"]
                    if max_length <= 0:
                        break
                    max_length -= 1

                bot.send_message(message.chat.id, text)

            else:
                print(f"Ошибка: {response.status_code}")
                bot.send_message(message.chat.id, f"При обработке комманды произошла ошибка, попробуйте повторить запрос")

        @bot.message_handler(commands=["kandinsky"])
        def kandinsky_command(message):
            add_users(message)
            prompt = message.text.strip()[(command_length(message) + 1):].title()
            if len(prompt) >= 1:
                print(f"--{prompt}--")
                bot.send_message(message.chat.id, "Изображение генерируется, надо немного подождать")
                kandinsky.kandinsky(prompt)
                file = open(path + "image.jpg", "rb")
                bot.send_photo(message.chat.id, file)
            else:
                bot.send_message(message.chat.id, "Слишком маленький запрос")

        @bot.message_handler(commands=["predict"])
        def predict_command(message):
            add_users(message)
            prompt = message.text.strip()[(command_length(message) + 1):].title()
            chat_id = message.chat.id
            if len(prompt) >= 1:
                if prompt[:4] == 'Кто ':
                    administrators = bot.get_chat_administrators(chat_id)  # Получаем список администраторов
                    name = 'my_ze_bot'
                    if len(administrators) > 1:
                        while name == 'my_ze_bot':
                            random_admin = random.choice(administrators)  # Выбираем случайного администратора
                            admin_name = random_admin.user.username  # Имя администратора

                            if admin_name:
                                bot.send_message(chat_id, f"Мне кажется, что @{admin_name} {prompt[4:].split('?')[0].lower()}")
                                name = admin_name
                            else:
                                bot.send_message(chat_id, f"Мне кажется, что {random_admin.user.nickname} {prompt[4:]}")
                                name = random_admin.user.nickname
                    else:
                        bot.send_message(chat_id, "В чате нет администраторов!")

                elif prompt[:4] == 'Где ':
                    answers = ["В другой реальности, но я не скажу в какой", "Ну точно не там, где нужно", "В пространстве между реальностями"]
                    bot.reply_to(message, random.choice(answers))

                else:
                    answers = ["да", "возможно", "нет", "не уверен", "пожалуй", "не думаю", "точно нет", "может быть", "смотря по ситуации", "не знаю", "конечно", "пока не могу сказать"]
                    bot.reply_to(message, random.choice(answers))
            else:
                bot.send_message(message.chat.id, "Слишком маленький запрос")

        @bot.message_handler(content_types=['voice'])
        def handle_voice(message):
            try:
                # Скачиваем голосовое сообщение
                file_info = bot.get_file(message.voice.file_id)
                downloaded_file = bot.download_file(file_info.file_path)

                # Сохраняем временно файл
                with open("voice.ogg", 'wb') as new_file:
                    new_file.write(downloaded_file)

                # Загружаем модель при первом вызове
                model_instance = get_model()

                # Распознаём речь
                segments, info = model_instance.transcribe("voice.ogg")

                # Собираем текст из всех сегментов
                recognized_text = ''
                for segment in segments:
                    recognized_text += segment.text + ' '

                # Отправляем текст обратно пользователю
                bot.reply_to(message, recognized_text.strip())

            except Exception as e:
                bot.reply_to(message, f"Ошибка при обработке голосового сообщения:\n{str(e)}")

        bot.polling(none_stop=True, timeout=123)

    except requests.exceptions.ReadTimeout:
        main()
    except requests.exceptions.ProxyError:
        main()


main()
