import telebot
from telebot import types
from datetime import datetime
import calendar
from calendar_helper import GoogleCalendarHelper
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Remove the hardcoded values and use environment variables
LOGS_CHANNEL_ID = os.getenv('LOGS_CHANNEL_ID')
bot = telebot.TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))

# Define TelegramLogHandler
class TelegramLogHandler(logging.Handler):
    def __init__(self, bot, channel_id):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id

    def emit(self, record):
        try:
            msg = self.format(record)
            formatted_msg = f"🔵 *{record.levelname}*\n" \
                          f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" \
                          f"📝 {msg}"
            self.bot.send_message(
                self.channel_id,
                formatted_msg,
                parse_mode='Markdown'
            )
        except Exception:
            self.handleError(record)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        TelegramLogHandler(bot, LOGS_CHANNEL_ID)
    ]
)
logger = logging.getLogger(__name__)

calendar_helper = GoogleCalendarHelper()

# Add after other configurations
LOGS_CHANNEL_ID = "YOUR_CHANNEL_ID"  # Replace with your channel ID

def generate_calendar(year, month, option):
    # Создание inline-календаря на указанный месяц и год
    markup = types.InlineKeyboardMarkup()

    # Название месяца и кнопки для навигации
    month_name = calendar.month_name[month]
    header = [
        types.InlineKeyboardButton("<<", callback_data=f"prev_month:{option}:{year}-{month}"),
        types.InlineKeyboardButton(month_name, callback_data="ignore"),
        types.InlineKeyboardButton(">>", callback_data=f"next_month:{option}:{year}-{month}")
    ]
    markup.row(*header)

    # Add weekday headers
    week_days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    markup.row(*[types.InlineKeyboardButton(day, callback_data="ignore") for day in week_days])

    # Get calendar dates
    cal = calendar.monthcalendar(year, month)

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                btn = types.InlineKeyboardButton(" ", callback_data="ignore")
            else:
                # Simply show the day number without any markers
                btn = types.InlineKeyboardButton(
                    str(day),
                    callback_data=f"select_date:{option}:{year}-{month}-{day}"
                )
            row.append(btn)
        markup.row(*row)

    # Add back button
    back_button = types.InlineKeyboardButton("« Назад", callback_data="back_to_options")
    markup.row(back_button)

    return markup

def generate_time_slots(option, date):
    markup = types.InlineKeyboardMarkup()
    busy_slots = calendar_helper.get_busy_slots(
        datetime.strptime(date, '%Y-%m-%d').date(),
        option
    )

    busy_hours = set()
    for slot in busy_slots:
        busy_hours.add(slot['hour'])

    for hour in range(10, 20):
        if hour in busy_hours:
            time_text = f"🔴 {hour}:00"
            callback_data = f"busy:{hour}:00"
        else:
            time_text = f"{hour}:00"  # Removed green marker
            callback_data = f"time:{option}:{date}:{hour}:00"

        time_button = types.InlineKeyboardButton(
            time_text,
            callback_data=callback_data
        )
        markup.add(time_button)

    # Add back button
    back_button = types.InlineKeyboardButton("« Назад", callback_data=f"back_to_calendar:{option}")
    markup.row(back_button)

    return markup


def generate_confirmation(option, date, time):
    markup = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton("Подтвердить", callback_data=f"confirm:{option}:{date}:{time}")
    back_button = types.InlineKeyboardButton("« Назад", callback_data=f"back_to_times:{option}:{date}")
    markup.row(confirm_button)
    markup.row(back_button)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Приветственное сообщение и кнопка "Забронировать"
    markup = types.InlineKeyboardMarkup()
    book_button = types.InlineKeyboardButton(text='Забронировать', callback_data='book')
    markup.add(book_button)
    bot.send_message(
        message.chat.id,
        "Добро пожаловать! Нажмите 'Забронировать', чтобы начать.",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'book')
def booking_options(call):
    # Buttons for different options
    markup = types.InlineKeyboardMarkup()
    first_button = types.InlineKeyboardButton(text='Бадминтон', callback_data='option:Бадминтон')
    second_button = types.InlineKeyboardButton(text='Сквош', callback_data='option:Сквош')
    markup.add(first_button, second_button)
    bot.edit_message_text(
        "Выберите опцию:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('option:'))
def show_calendar(call):
    # Показать календарь для текущего месяца
    option = call.data.split(':')[1]
    now = datetime.now()
    year, month = now.year, now.month
    markup = generate_calendar(year, month, option)
    bot.edit_message_text(
        f"Календарь: {calendar.month_name[month]} {year}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('prev_month') or call.data.startswith('next_month'))
def change_month(call):
    # Навигация по месяцам
    action, option, date_info = call.data.split(':')
    year, month = map(int, date_info.split('-'))

    if action == 'prev_month':
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    elif action == 'next_month':
        month += 1
        if month == 13:
            month = 1
            year += 1

    markup = generate_calendar(year, month, option)
    bot.edit_message_text(
        f"Календарь: {calendar.month_name[month]} {year}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_date:'))
def handle_date_selection(call):
    # Обработка выбранной даты
    try:
        _, option, date = call.data.split(':')
        markup = generate_time_slots(option, date)
        bot.edit_message_text(
            f"Вы выбрали {option} на {date}. Выберите время:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except ValueError:
        bot.answer_callback_query(call.id, "Произошла ошибка при обработке даты.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('time:'))
def handle_time_selection(call):
    try:
        parts = call.data.split(':')
        if len(parts) >= 4:
            _, option, date, time = parts[:4]
            markup = generate_confirmation(option, date, time)
            bot.edit_message_text(
                f"Вы выбрали: \nВид спорта: {option}\nДата: {date}\nВремя: {time}\nНажмите 'Подтвердить' для завершения.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        else:
            raise ValueError("Неверный формат")
    except Exception as e:
        bot.answer_callback_query(call.id, "Ошибка при выборе времени")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm:'))
def handle_confirmation(call):
    try:
        # Send "Бронируем" message with sticker
        message = bot.edit_message_text(
            "Бронируем...",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        sticker_message = bot.send_sticker(
            call.message.chat.id,
            os.getenv('LOADING_STICKER_ID')
        )

        _, option, date, time = call.data.split(':')
        logger.info(f"Processing booking: Sport={option}, Date={date}, Time={time}")

        # Parse the date and add leading zeros
        year, month, day = map(int, date.split('-'))
        formatted_date = f"{year}-{month:02d}-{day:02d}"

        # Format times in RFC3339 format
        hour = int(time.split(':')[0])
        start_time = datetime(year, month, day, hour, 0).isoformat() + '+03:00'
        end_time = datetime(year, month, day, hour + 1, 0).isoformat() + '+03:00'

        event = {
            'summary': f'{option} Booking',
            'description': f'Booked via Telegram Bot\nUser ID: {call.from_user.id}',
            'start': {
                'dateTime': start_time,
                'timeZone': 'Europe/Moscow',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Europe/Moscow',
            },
            'reminders': {'useDefault': True},
            'transparency': 'opaque',
            'status': 'confirmed',
            'extendedProperties': {
                'private': {
                    'userId': str(call.from_user.id)
                }
            }
        }

        created_event = calendar_helper.create_event(event, option)

        # Delete the sticker message
        bot.delete_message(call.message.chat.id, sticker_message.message_id)

        # Show confirmation and new booking option
        bot.edit_message_text(
            f"✅ Бронирование подтверждено!\n\nВид спорта: {option}\nДата: {formatted_date}\nВремя: {time}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

        markup = types.InlineKeyboardMarkup()
        book_button = types.InlineKeyboardButton(text='Забронировать', callback_data='book')
        markup.add(book_button)
        bot.send_message(
            call.message.chat.id,
            "Нажмите 'Забронировать', чтобы начать.",
            reply_markup=markup
        )

    except Exception as e:
        # Clean up sticker if there was an error
        try:
            bot.delete_message(call.message.chat.id, sticker_message.message_id)
        except:
            pass
        logger.error(f"Booking error: {str(e)}", exc_info=True)
        bot.answer_callback_query(call.id, "Ошибка при бронировании")

@bot.callback_query_handler(func=lambda call: call.data.startswith('back_to_options'))
def back_to_options(call):
    markup = types.InlineKeyboardMarkup()
    first_button = types.InlineKeyboardButton(text='Бадминтон', callback_data='option:Бадминтон')
    second_button = types.InlineKeyboardButton(text='Сквош', callback_data='option:Сквош')
    markup.add(first_button, second_button)
    bot.edit_message_text(
        "Выберите опцию:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('back_to_calendar:'))
def back_to_calendar(call):
    option = call.data.split(':')[1]
    now = datetime.now()
    year, month = now.year, now.month
    markup = generate_calendar(year, month, option)
    bot.edit_message_text(
        f"Календарь: {calendar.month_name[month]} {year}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('back_to_times:'))
def back_to_times(call):
    _, option, date = call.data.split(':')
    markup = generate_time_slots(option, date)
    bot.edit_message_text(
        f"Вы выбрали {option} на {date}. Выберите время:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True)
def fallback_message(message):
    # Ответ на любое другое текстовое сообщение
    bot.send_message(
        message.chat.id,
        "Нажми /start чтобы перейти к бронированию."
    )

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
