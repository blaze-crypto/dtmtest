
import random
import string
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_IDS, CHANNELS, logger
import io
import xlsxwriter


def generate_test_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def calculate_score(user_answers: str, correct_answers: str) -> float:
    user_ans_list = user_answers.split(',')
    correct_ans_list = correct_answers.split(',')
    correct_count = sum(1 for u, c in zip(user_ans_list, correct_ans_list) if u.strip() == c.strip())
    return (correct_count / len(correct_ans_list)) * 100

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📝 Test yaratish", callback_data="create_test"),
                 InlineKeyboardButton("🖍 Test ishlash", callback_data="take_test"))
    keyboard.row(InlineKeyboardButton("📊 Testlarim", callback_data="my_tests"),
                 InlineKeyboardButton("🏆 Reyting", callback_data="leaderboard"))
    keyboard.row(InlineKeyboardButton("🆘 Yordam", callback_data="help"))
    return keyboard


def admin_menu_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📊 Foydalanuvchi statistikasi", callback_data="admin_stats"))
    keyboard.row(InlineKeyboardButton("📩 Xabar jo'natish", callback_data="admin_broadcast"))
    keyboard.row(InlineKeyboardButton("👥 Foydalanuvchilar ro'yxati", callback_data="admin_users"))
    keyboard.row(InlineKeyboardButton("🔍 Test qidirish", callback_data="admin_search_test"))
    keyboard.row(InlineKeyboardButton("🗑 Eski testlarni o'chirish", callback_data="admin_delete_old_tests"))
    keyboard.row(InlineKeyboardButton("🏠 Asosiy menyu", callback_data="main_menu"))
    return keyboard



def channel_sub_keyboard():
    keyboard = InlineKeyboardMarkup()
    for i, channel in enumerate(CHANNELS, 1):
        keyboard.row(InlineKeyboardButton(f"{i}-kanalga obuna bo'lish", url=channel['url']))
    keyboard.row(InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub"))
    return keyboard

def phone_number_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True))
    return keyboard

def edit_test_keyboard(test_codes):
    keyboard = InlineKeyboardMarkup()
    for code in test_codes:
        keyboard.row(InlineKeyboardButton(f"Test: {code}", callback_data=f"edit_{code}"))
    return keyboard

def is_admin(user_id: int) -> bool:
    is_admin = user_id in ADMIN_IDS
    logger.debug(f"Checking admin status for user {user_id}: {is_admin}")
    return is_admin

def check_sub(user_id, bot):
    for channel in CHANNELS:
        try:
            member = bot.get_chat_member(f"@{channel['username']}", user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            print(f"Error checking subscription for channel {channel['username']}: {e}")
            return False
    return True

def generate_excel_report(test_code, stats):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Add some cell formats.
    bold = workbook.add_format({'bold': True})
    date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})

    # Increase column width for better readability
    worksheet.set_column('A:G', 20)

    headers = ['Foydalanuvchi', 'Username', 'Telefon', 'Natija', 'Javoblar', 'Topshirilgan vaqt', 'Urinishlar soni']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, bold)

    for row, stat in enumerate(stats, start=1):
        worksheet.write(row, 0, stat['name'])
        worksheet.write(row, 1, stat['username'])
        worksheet.write(row, 2, stat['phone'])
        worksheet.write(row, 3, f"{stat['score']:.2f}%")
        worksheet.write(row, 4, stat['user_answers'])
        worksheet.write_datetime(row, 5, stat['submitted_at'], date_format)
        worksheet.write(row, 6, stat['attempt_count'])

    workbook.close()
    output.seek(0)
    return output
