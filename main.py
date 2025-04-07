# -*- coding: utf-8 -*-
import configparser
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
import json
import re
import os
import io
from collections import Counter


config = configparser.ConfigParser()
config.read('setting.ini')

state_storage = StateMemoryStorage()
token_bot = config['Token']['tg_token']
group_id = config['Token']['group']

bot = TeleBot(token_bot)

buttons = []
ESTIMATION = [str(i) for i in range(11)]


def loading_json():
    file_name = 'data.json'
    if os.path.isfile(file_name):
        with io.open(file_name, "r", encoding="utf-8", errors="ignore") as f:
            user_information_json = json.load(f)
            return user_information_json
    else:
        print(f'Файла {file_name} нету. Значит будет все с нуля')
        return {}

user_information_json = loading_json()


def count_number():
    count = len(user_information_json)
    return count + 1


def save_json():
    with open('data.json', 'w', encoding='utf-8') as file:
        json.dump(user_information_json, file,
                  ensure_ascii=False, indent=4)


def format_phone_number(phone):
    # Удаляем все символы, кроме цифр
    phone_re = re.sub(r'\D', '', phone)
    # Если номер начинается с 8, заменяем на 7
    if phone_re.startswith('8'):
        phone_re = '7' + phone_re[1:]
    # Добавляем + в начале, если его нет
    if not phone_re.startswith('+'):
        phone_re = '+7' + phone_re[1:] if phone_re.startswith('7')\
            else '+7' + phone_re
    return phone_re


@bot.message_handler(commands=['start'])
def start(message):
    name = str()
    cid = message.chat.id
    if len(message.text) > 6:
        order_number = message.text.split('_')[1]
    else:
        return bot.send_message(message.chat.id, f'Вы перешли не через qr-код.'
                                f' Отсканируйте направленный вам qr-код')

    if 'kazn' in order_number:
        number = re.search(r'\d+', order_number)
        order_number = 'КАЗН' + str(number.group())
    elif 'vtzn' in order_number:
        number = re.search(r'\d+', order_number)
        order_number = 'ВТЗН' + str(number.group())

    if message.from_user.last_name is not None:
        name = message.from_user.last_name
    if message.from_user.first_name is not None:
        if name == '':
            name = message.from_user.first_name
        else:
            name = name + f' {message.from_user.first_name}'
    if order_number in user_information_json:
        bot.send_message(message.chat.id, f'Заказ {order_number}.\n'
                                          f'Уже оценен.')
        return
    else:
        user_information_json[order_number] = {
            'Name': name,
            'Cid': cid,
            'Phone' : str(),
            'Estimation' : -1,
            'Feedback' : str(),
            'Question_date' : datetime.now().strftime('%d.%m.%Y %H:%M'),
            'Number' : count_number()
        }
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    reg_button = types.KeyboardButton(text="Отправить номер телефона",
                                      request_contact=True)
    keyboard.add(reg_button)
    bot.send_message(message.chat.id, f'Здравствуйте {name}. '
                                      f'Нам важен ваш отзыв по заказу '
                                      f'{order_number}. '
                                      f'Нажмите на кнопку '
                                      f'"Отправить номер телефона".',
                     reply_markup=keyboard)


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    # Удаление кнопок
    contact = format_phone_number(message.contact.phone_number)
    cid = message.chat.id
    order_number = str()
    bot.send_message(cid, "Спасибо, что поделились номером.",
                     reply_markup=types.ReplyKeyboardRemove())
    for key_dict, value_dict in user_information_json.items():
        if value_dict['Cid'] == cid and value_dict['Phone'] == '':
            order_number = key_dict
            break

    user_information_json[order_number]['Phone'] = contact
    # Создание кнопок через InlineKeyboardMarkup
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    buttons = []
    for i in range(10, -1, -1):
        button = types.InlineKeyboardButton(text=str(i), callback_data=str(i))
        buttons.append(button)
    keyboard.add(*buttons)
    bot.send_message(cid, f'Оцените заказ от 0 до 10.',
                    reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data in ESTIMATION)
def callback_inline(call):
    cid = call.message.chat.id
    estimation = int(call.data)
    order_number = str()
    bot.send_message(cid, f"Ваша оценка {estimation}/10 принята.",
                     reply_markup=types.ReplyKeyboardRemove())
    for key_dict, value_dict in user_information_json.items():
        if value_dict['Cid'] == cid and value_dict['Estimation'] == -1:
            order_number = key_dict
            break
    user_information_json[order_number]['Estimation'] = estimation
    bot.send_message(cid, f'Просим вас оставить отзыв по вашему заказу.')


@bot.message_handler(func=lambda message: True and '/' not in message.text)
def feedback_add(message):
    cid = message.chat.id
    feedback = message.text
    if feedback == '':
        feedback = ' '
    order_number = str()
    for key_dict, value_dict in user_information_json.items():
        if value_dict['Cid'] == cid and value_dict['Feedback'] == '':
            order_number = key_dict
            break
    user_information_json[order_number]['Feedback'] = feedback
    bot.send_message(message.chat.id, f'Спасибо за Ваш комментарий к заказу.')
    save_json()
    name = user_information_json[order_number]['Name']
    phone = user_information_json[order_number]['Phone']
    estimation = user_information_json[order_number]['Estimation']
    feedback = user_information_json[order_number]['Feedback']
    number = user_information_json[order_number]['Number']
    text = f'''📊 ОПРОС #{number}
    ------------------------------
    Заказ-наряд: {order_number}
    Клиент: {name}
    Телефон: {phone}
    Оценка: {estimation}/10
    Комментарий: {feedback}'''
    bot.send_message(group_id, text)


@bot.message_handler(commands=['table'])
def table_(message):
    cid = message.chat.id
    # Создание кнопок через InlineKeyboardMarkup
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    TEXT_ = {'За месяц': 'month', 'За квартал': 'quarter', 'За год': 'year'}
    for key, value in TEXT_.items():
        button = types.InlineKeyboardButton(text=key, callback_data=value)
        buttons.append(button)
    keyboard.add(*buttons)
    bot.send_message(cid, f'Выберите период',
                     reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data in
                            ['month', 'quarter', 'year'])
def callback_table(call):
    cid = call.message.chat.id
    TEXT_dict = {'month': 'за месяц','quarter': 'за квартал', 'year': 'за год'}
    TEXT_ = call.data
    date = datetime.now()
    date_back = str()
    if TEXT_ == 'month':
        date_back = date - relativedelta(months=1)
    elif TEXT_ == 'quarter':
        date_back = date - relativedelta(months=3)
    elif TEXT_ == 'year':
        date_back = date - relativedelta(years=1)
    recent_feedbacks = [
        f for f in user_information_json.values()
        if datetime.strptime(f['Question_date'], '%d.%m.%Y %H:%M') >= date_back
    ]
    total_feedbacks = len(recent_feedbacks)
    feedback_by_estimation = Counter(f['Estimation'] for f in recent_feedbacks)
    # Формирование отчета
    report = f"📊 Статистика отзывов {TEXT_dict[TEXT_]}:\n"
    report += f"🔹 Всего отзывов: {total_feedbacks}\n"
    report += "🔹 Оценки:\n"
    for estimation in range(10, -1, -1):
        count = feedback_by_estimation.get(estimation, 0)
        if count > 0:
            report += f"  • Оценка {estimation}: {count} отзывов\n"

    bot.send_message(group_id, report)


@bot.message_handler(commands=['save'])
def save(message):
    cid = message.chat.id
    save_json()
    bot.send_message(cid, f'Данные сохранены, можно выключать бота')


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
