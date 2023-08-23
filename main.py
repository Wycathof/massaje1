import telebot
from telebot import types

bot = telebot.TeleBot('6643898025:AAE4U1KyPJs0iupw1YZA3m_aCfmDNHQmCu4')
ADMIN_CHAT_ID = '6119033891'

schedule = {
    '2022-01-01': ['10:00', '12:00', '14:00', '16:00'],
    '2022-01-02': ['12:00', '14:00', '16:00', '18:00'],
    '2022-01-03': ['9:00', '11:00', '14:00', '17:00'],
}

services = ['Маникюр', 'Педикюр', 'Наращивание ногтей']
clients = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет! Выберите услугу, на которую хотите записаться', reply_markup=create_services_selection())

def create_services_selection():
    services_markup = types.InlineKeyboardMarkup()
    for service in services:
        button = types.InlineKeyboardButton(text=service, callback_data=f'select_service|{service}')
        services_markup.add(button)
    return services_markup

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_service'))
def callback_service_selected(call):
    service = call.data.split('|')[1]
    clients[call.message.chat.id] = {'service': service}
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'Выбрана услуга {service}. Теперь выберите дату', reply_markup=create_calendar())

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_date'))
def callback_date_selected(call):
    date = call.data.split('|')[1]
    clients[call.message.chat.id]['date'] = date
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Теперь выберите время', reply_markup=create_time_selection(date))

@bot.callback_query_handler(func=lambda call: call.data.startswith('back_to_date'))
def callback_back_to_date(call):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Выберите услугу, на которую хотите записаться', reply_markup=create_services_selection())

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_time'))
def callback_time_selected(call):
    user_id = call.message.chat.id
    _, date, time = call.data.split('|')
    if not is_available(date, time):
        bot.send_message(user_id, 'Это время занято, выберите другое')
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, create_time_selection(date))
        return
    clients[user_id]['time'] = time
    service = clients[user_id]['service']
    bot.send_message(user_id, f'Ты записан на {service} {date} в {time}. Спасибо!')
    notify_admin(user_id, service, date, time)
    remove_time_from_schedule(date, time)
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text='Успешно записан на услугу! Выберите услугу, на которую хотите записаться', reply_markup=create_services_selection())

@bot.message_handler(commands=['schedule'])
def send_schedule(message):
    schedule_text = 'Моё расписание на следующий месяц:\n'
    for date, times in schedule.items():
        schedule_text += date + '\n'
        schedule_text += '\n'.join(times) + '\n\n'
    bot.send_message(message.chat.id, schedule_text)

@bot.message_handler(commands=['cancel'])
def cancel_message(message):
    user_id = message.chat.id
    if user_id in clients:
        date, time = clients[user_id]['date'], clients[user_id]['time']
        if time in schedule[date]:
            bot.send_message(user_id, f'Отменено. Время {time} ({date}) освободилось')
            notify_admin_cancelled(user_id, date, time)
            schedule[date].remove(time)
        else:
            bot.send_message(user_id, 'Выбранное время уже занято. Выберите другое время.')
        del clients[user_id]
    else:
        bot.send_message(user_id, 'Для отмены запиcи нужно сделать ее сначала.')

@bot.message_handler(commands=['clients'])
def send_clients_list(message):
    if message.from_user.id == 6119033891:
        clients_list = 'Список записавшихся клиентов:\n'
        for chat_id, data in clients.items():
            clients_list += f'{chat_id}: {data["service"]} {data["date"]} {data["time"]}\n'
        bot.send_message(message.chat.id, clients_list)
    else:
        bot.send_message(message.chat.id, "У тебя нет доступа. К сожалению и не будет, потому что админская команда.")

def create_calendar():
    calendar = types.InlineKeyboardMarkup()
    for date, _ in schedule.items():
        button = types.InlineKeyboardButton(text=date, callback_data=f'select_date|{date}')
        calendar.add(button)
    back_button = types.InlineKeyboardButton(text="Назад", callback_data="back_to_date")
    calendar.row(back_button)
    return calendar

def create_time_selection(date):
    times = schedule[date]
    time_selection = types.InlineKeyboardMarkup()
    for time in times:
        button = types.InlineKeyboardButton(text=time, callback_data=f'select_time|{date}|{time}')
        time_selection.add(button)
    return time_selection

def is_available(date, time):
    return time in schedule[date]

def remove_time_from_schedule(date, time):
    schedule[date].remove(time)

def notify_admin(user_id, service, date, time):
    message = bot.send_message(ADMIN_CHAT_ID, f'Новый клиент записался на {service}: {user_id}, {date} {time}. Подтвердить запись?', reply_markup=create_confirmation_keyboard(user_id))

def create_confirmation_keyboard(user_id):
    confirmation_keyboard = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton(text='Подтвердить', callback_data=f'confirm|{user_id}')
    cancel_button = types.InlineKeyboardButton(text='Отменить', callback_data=f'cancel|{user_id}')
    back_button = types.InlineKeyboardButton(text="Назад", callback_data=f'back_to_clients|{user_id}')
    confirmation_keyboard.row(confirm_button, cancel_button).add(back_button)
    return confirmation_keyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm'))
def callback_confirm_selected(call):
    user_id = int(call.data.split('|')[1])
    if user_id in clients:
        bot.send_message(user_id, 'Запись подтверждена!')
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    else:
        bot.send_message(user_id, 'Извините, все записи уже заняты. Выберите другое время.')
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel'))
def callback_cancel_selected(call):
    user_id = int(call.data.split('|')[1])
    if user_id in clients:
        date, time = clients[user_id]['date'], clients[user_id]['time']
        schedule[date].append(time)
        del clients[user_id]
        bot.send_message(user_id, f'Ваша запись на маникюр была отменена. Вы можете записаться на другое время.')
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    else:
        bot.send_message(user_id, 'К сожалению, ваша запись уже была отменена или не существует.')
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('back_to_clients'))
def callback_back_to_clients(call):
    user_id = int(call.data.split('|')[1])
    bot.answer_callback_query(call.id)

def notify_admin_cancelled(user_id, date, time):
    bot.send_message(ADMIN_CHAT_ID, f'Клиент отменил запись на маникюр: {user_id}, {date} {time}')

bot.polling()
