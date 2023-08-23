import telebot
from telebot import types

bot = telebot.TeleBot('6643898025:AAE4U1KyPJs0iupw1YZA3m_aCfmDNHQmCu4')
ADMIN_CHAT_ID = '6119033891'

schedule = {
    '2022-01-01': ['10:00', '12:00', '14:00', '16:00'],
    '2022-01-02': ['12:00', '14:00', '16:00', '18:00'],
    '2022-01-03': ['9:00', '11:00', '14:00', '17:00'],
}

clients = {}


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет! Чтобы записаться на маникюр, выбери дату и время',
                     reply_markup=create_calendar())


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_date'))
def callback_date_selected(call):
    date = call.data.split('|')[1]
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f'Выбрана дата {date}. Теперь выбери время', reply_markup=create_time_selection(date))


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_time'))
def callback_time_selected(call):
    _, date, time = call.data.split('|')
    if is_available(date, time):
        clients[call.message.chat.id] = {'date': date, 'time': time}
        bot.send_message(call.message.chat.id, f'Ты записан на {date} в {time}. Спасибо!')
        notify_admin(call.message.chat.id, date, time)
        remove_time_from_schedule(date, time)
    else:
        bot.send_message(call.message.chat.id, 'Это время занято, выбери другое')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                  reply_markup=create_time_selection(date))


@bot.message_handler(commands=['schedule'])
def send_schedule(message):
    schedule_text = 'Моё расписание на следующий месяц:\n'
    for date, times in schedule.items():
        schedule_text += date + '\n'
        schedule_text += '\n'.join(times) + '\n\n'
    bot.send_message(message.chat.id, schedule_text)


@bot.message_handler(commands=['cancel'])
def cancel_message(message):
    if message.chat.id in clients:
        date, time = clients[message.chat.id]['date'], clients[message.chat.id]['time']
        schedule[date].append(time)
        del clients[message.chat.id]
        bot.send_message(message.chat.id, f'Отменено. Время {time} ({date}) освободилось')
        notify_admin_cancelled(message.chat.id, date, time)


@bot.message_handler(commands=['clients'])
def send_clients_list(message):
    if message.from_user.id == ADMIN_CHAT_ID:
        clients_list = 'Список записавшихся клиентов:\n'
        for chat_id, data in clients.items():
            clients_list += f'{chat_id}: {data["date"]} {data["time"]}\n'
        bot.send_message(message.chat.id, clients_list)
    else:
        bot.send_message(message.chat.id, "У тебя нет доступа. К сожалению и не будет, потому что админская команда.")


def create_calendar():
    calendar = types.InlineKeyboardMarkup()
    for date, times in schedule.items():
        button = types.InlineKeyboardButton(text=date, callback_data=f'select_date|{date}')
        calendar.add(button)
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


def notify_admin(user_id, date, time):
    message = bot.send_message(ADMIN_CHAT_ID,
                               f'Новый клиент записался на маникюр: {user_id}, {date} {time}. Подтвердить запись?',
                               reply_markup=create_confirmation_keyboard(user_id))


def create_confirmation_keyboard(user_id):
    confirmation_keyboard = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton(text='Подтвердить', callback_data=f'confirm|{user_id}')
    cancel_button = types.InlineKeyboardButton(text='Отменить', callback_data=f'cancel|{user_id}')
    confirmation_keyboard.add(confirm_button, cancel_button)
    return confirmation_keyboard


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm'))
def callback_confirm_selected(call):
    user_id = int(call.data.split('|')[1])
    if user_id in clients:
        bot.send_message(user_id, 'Запись подтверждена!')
    else:
        bot.send_message(user_id, 'Извините, все записи уже заняты. Выберите другое время.')

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel'))
def callback_cancel_selected(call):
    user_id = int(call.data.split('|')[1])
    if user_id in clients:
        date, time = clients[user_id]['date'], clients[user_id]['time']
        schedule[date].append(time)
        del clients[user_id]
        bot.send_message(user_id, 'Ваша запись на маникюр была отменена. Вы можете записаться на другое время.')
    else:
        bot.send_message(user_id, 'К сожалению, ваша запись уже была отменена или не существует.')

    bot.answer_callback_query(call.id)


def notify_admin_cancelled(user_id, date, time):
    bot.send_message(ADMIN_CHAT_ID, f'Клиент отменил запись на маникюр: {user_id}, {date} {time}')


bot.polling()
