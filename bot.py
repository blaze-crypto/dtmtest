import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import TOKEN, logger, ADMIN_IDS, CHANNELS
from database import (create_tables, register_user, is_user_registered, create_test, get_test,
                      update_test, save_test_result, get_user_stats, get_all_user_ids, get_user_tests,
                      get_test_statistics, get_user_info, generate_users_csv, update_user_username, add_test_scores,
                      get_test_scores, get_user_test_attempts, delete_old_tests, get_leaderboard, search_test,
                      get_test_by_id, get_all_users)
from utils import (calculate_score, is_admin, phone_number_keyboard, channel_sub_keyboard,
                   check_sub, main_menu_keyboard, admin_menu_keyboard, edit_test_keyboard, generate_excel_report)
import csv
import io
from datetime import datetime, timedelta

bot = telebot.TeleBot(TOKEN)

create_tables()

def subscription_required(func):
    def wrapper(message):
        if check_sub(message.from_user.id, bot):
            return func(message)
        else:
            bot.send_message(message.chat.id, "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=channel_sub_keyboard())
    return wrapper

@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f"User {message.from_user.id} started the bot")
    update_user_username(message.from_user.id, message.from_user.username)
    if check_sub(message.from_user.id, bot):
        if not is_user_registered(message.from_user.id):
            bot.reply_to(message, "Ism va familiyangizni kiriting.")
            bot.register_next_step_handler(message, process_name)
        else:
            show_main_menu(message)
    else:
        bot.send_message(message.chat.id, "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=channel_sub_keyboard())

def process_name(message):
    name = message.text
    logger.info(f"Processing name for user {message.from_user.id}: {name}")
    bot.reply_to(message, "Telefon raqamingizni yuboring:", reply_markup=phone_number_keyboard())
    bot.register_next_step_handler(message, process_phone, name)

def process_phone(message, name):
    if message.contact is not None:
        phone = message.contact.phone_number
        username = message.from_user.username
        logger.info(f"Processing phone for user {message.from_user.id}: {phone}")
        register_user(message.from_user.id, name, phone, username)
        bot.reply_to(message, f"Rahmat, {name}! Siz muvaffaqiyatli ro'yxatdan o'tdingiz.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True))
        show_main_menu(message)
    else:
        bot.reply_to(message, "Iltimos, telefon raqamingizni yuborish uchun tugmani bosing.")
        bot.register_next_step_handler(message, process_phone, name)

def show_main_menu(message):
    keyboard = main_menu_keyboard()
    if is_admin(message.from_user.id):
        keyboard.row(InlineKeyboardButton("👑 Admin panel", callback_data="admin_panel"))
    bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "check_sub":
        if check_sub(call.from_user.id, bot):
            bot.answer_callback_query(call.id, "Siz muvaffaqiyatli obuna bo'ldingiz!")
            if not is_user_registered(call.from_user.id):
                bot.send_message(call.message.chat.id, "Ism va familiyangizni kiriting.")
                bot.register_next_step_handler(call.message, process_name)
            else:
                show_main_menu(call.message)
        else:
            bot.answer_callback_query(call.id, "Siz hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)
    elif call.data == "create_test":
        create_test_handler(call.message)
    elif call.data == "take_test":
        take_test_handler(call.message)
    elif call.data == "my_tests":
        my_tests_handler(call.message)
    elif call.data == "leaderboard":
        show_leaderboard(call.message)
    elif call.data == "help":
        help_handler(call.message)
    elif call.data == "admin_panel":
        if is_admin(call.from_user.id):
            show_admin_panel(call.message)
        else:
            bot.answer_callback_query(call.id, "Sizda bu amalni bajarish uchun huquq yo'q!")
    elif call.data == "admin_stats":
        admin_stats(call.message)
    elif call.data == "admin_broadcast":
        admin_broadcast(call.message)
    elif call.data == "admin_users":
        admin_users(call.message)
    elif call.data == "admin_search_test":
        admin_search_test(call.message)
    elif call.data == "admin_delete_old_tests":
        admin_delete_old_tests(call.message)
    elif call.data.startswith("edit_"):
        test_code = call.data.split("_")[1]
        edit_test_handler(call.message, test_code)
    elif call.data.startswith("stats_"):
        test_code = call.data.split("_")[1]
        show_test_statistics(call.message, test_code)
    elif call.data == "add_scores":
        add_scores_handler(call.message)
    elif call.data == "cancel":
        bot.answer_callback_query(call.id, "Amal bekor qilindi.")
        show_main_menu(call.message)
    elif call.data == "main_menu":
        show_main_menu(call.message)

@subscription_required
def create_test_handler(message):
    logger.info(f"User {message.chat.id} initiated test creation")
    bot.send_message(message.chat.id, 
    """
    ❗️ Yangi test yaratish

    ✅ Test kodini, nomini va kalitlarni quyidagi formatda kiriting:
    TestKodi|TestNomi+abcdabcdabcd...

    ✍️ Misol uchun: 
    MATH101|Matematika+abcdabcdabcd...  yoki
    PHYS2023|Fizika+1a2b3c4d5a6b7c...

    ✅ Test kodi faqat harflar va raqamlardan iborat bo'lishi kerak.
    ✅ Katta(A) va kichik(a) harflar bir xil hisoblanadi.

    🗄 Test natijalari 30 kun saqlanadi
    """)
    bot.register_next_step_handler(message, process_test_creation)

def process_test_creation(message):
    if message.text is None:
        bot.reply_to(message, "Iltimos, matn formatida xabar yuboring. Rasm, stiker yoki boshqa turdagi xabarlar qabul qilinmaydi.")
        create_test_handler(message)
        return

    if message.text == "Bekor qilish":
        return cancel_operation(message)
    
    try:
        code_and_content = message.text.split('|')
        if len(code_and_content) != 2:
            raise ValueError("Noto'g'ri format")
        
        code = code_and_content[0].strip().upper()
        test_name, answers = code_and_content[1].split('+')
        test_name = test_name.strip()
        answers = answers.strip().lower()
        
        if not code.isalnum():
            raise ValueError("Test kodi faqat harflar va raqamlardan iborat bo'lishi kerak")
        
        if get_test(code):
            raise ValueError("Bu test kodi allaqachon mavjud")
        
        create_test(message.chat.id, code, answers, test_name)
        
        response = f"""
        ✅️ Test ishlanishga tayyor
        🗒 Test nomi: {test_name}
        🔢 Testlar soni: {len(answers)} ta
        ‼️‼️ Test kodi: {code}
        👤 Test yaratuvchisi: {message.from_user.first_name} {message.from_user.last_name}

        Test javoblaringizni quyidagi botga jo'nating:

        👉 @{bot.get_me().username}
        👉 @{bot.get_me().username}
        👉 @{bot.get_me().username}

        📌 Testda qatnashuvchilar quyidagi ko`rinishda javob yuborishlari mumkin:
        Test kodini kiriting va *(yulduzcha) belgisini qo'ying.
        To'liq {len(answers)} ta javobni ham kiriting.  

        Namuna:
        {code}*abcdab... ({len(answers)} ta)   yoki
        {code}*1a2b3c4d5a6b... ({len(answers)} ta)
            
        ♻️ Test ishlanishga tayyor!!!
        """
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("Test ma'lumotlarini ko'rish", callback_data=f"stats_{code}"))
        keyboard.row(InlineKeyboardButton("Ball qo'shish", callback_data="add_scores"))
        keyboard.row(InlineKeyboardButton("🏠 Asosiy menyu", callback_data="main_menu"))
        
        bot.send_message(message.chat.id, response, reply_markup=keyboard)
    except ValueError as e:
        bot.reply_to(message, f"Xatolik yuz berdi: {str(e)}. Iltimos, qaytadan urinib ko'ring.")
        create_test_handler(message)

@subscription_required
def take_test_handler(message):
    logger.info(f"User {message.chat.id} initiated test taking")
    bot.send_message(message.chat.id, 
    """
    ❗️Testga javob berish

    ✅ Test kodini kiritib * (yulduzcha) belgisini qo'yasiz va barcha kalitlarni kiritasiz.

    ✍️ Misol uchun: 
    123*abcdabcdabcd...  yoki
    123*1a2b3c4d5a6b7c...

    ⁉️ Testga faqat bir marta javob berish mumkin.

    ✅ Katta(A) va kichik(a) harflar bir xil hisoblanadi.
    """)
    bot.register_next_step_handler(message, process_test_taking)

def process_test_taking(message):
    if message.text is None:
        bot.reply_to(message, "Iltimos, matn formatida xabar yuboring. Rasm, stiker yoki boshqa turdagi xabarlar qabul qilinmaydi.")
        take_test_handler(message)
        return

    try:
        code, answers = message.text.split('*')
        code = code.strip()
        answers = answers.strip().lower()
        test = get_test(code)
        if test:
            user_attempts = get_user_test_attempts(message.chat.id, test['id'])
            if user_attempts and user_attempts['attempt_count'] >= 1:
                bot.reply_to(message, "⚠️ Siz bu testni allaqachon ishlagansiz. Har bir testni faqat bir marta ishlash mumkin.")
                return

            score = calculate_score(answers, test['answers'])
            save_test_result(message.chat.id, test['id'], score, answers)
            
            response = f"""
            ✅ Test muvaffaqiyatli topshirildi!
            🗒 Test nomi: {test['name']}
            🔢 To'g'ri javoblar soni: {int(score * len(test['answers']) / 100)} ta
            📊 Natija: {score:.2f}%
            """
            
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("🏠 Asosiy menyu", callback_data="main_menu"))
            
            bot.send_message(message.chat.id, response, reply_markup=keyboard)
            
            creator_id = test['creator_id']
            user_info = get_user_info(message.chat.id)
            creator_message = f"""
            👤 Foydalanuvchi testingizni ishladi:
            📛 Ism: {user_info['name']}
            🆔 Username: @{user_info['username']}
            📊 Natija: {score:.2f}%
            """
            bot.send_message(creator_id, creator_message)
        else:
            bot.reply_to(message, "Noto'g'ri test kodi. Iltimos, qaytadan urinib ko'ring.")
            take_test_handler(message)
    except ValueError:
        bot.reply_to(message, "Xatolik yuz berdi. Iltimos, to'g'ri formatda kiriting.")
        take_test_handler(message)

@subscription_required
def my_tests_handler(message):
    tests = get_user_tests(message.chat.id)
    if tests:
        logger.info(f"User {message.chat.id} requested their tests. Found {len(tests)} tests.")
        keyboard = InlineKeyboardMarkup()
        for test in tests:
            keyboard.row(
                InlineKeyboardButton(f"📝 {test['name']} ({test['code']})", callback_data=f"edit_{test['code']}"),
                InlineKeyboardButton("📊 Statistika", callback_data=f"stats_{test['code']}")
            )
        keyboard.row(InlineKeyboardButton("🏠 Asosiy menyu", callback_data="main_menu"))
        bot.send_message(message.chat.id, "Sizning testlaringiz:", reply_markup=keyboard)
    else:
        logger.info(f"User {message.chat.id} requested their tests. No tests found.")
        bot.send_message(message.chat.id, "Siz hali test yaratmagansiz.")

def edit_test_handler(message, test_code):
    test = get_test(test_code)
    if test:
        response = f"""
        🗒 Test nomi: {test['name']}
        🔢 Testlar soni: {len(test['answers'])} ta
        ‼️ Test kodi: {test['code']}

        Joriy javoblar: {test['answers']}

        Yangi test nomini va javoblarni quyidagi formatda kiriting:
        YangiTestNomi+abcdabcd...
        """
        bot.send_message(message.chat.id, response)
        bot.register_next_step_handler(message, process_test_edit, test_code)
    else:
        bot.send_message(message.chat.id, "Noto'g'ri test kodi.")

def process_test_edit(message, test_code):
    if message.text is None:
        bot.reply_to(message, "Iltimos, matn formatida xabar yuboring. Rasm, stiker yoki boshqa turdagi xabarlar qabul qilinmaydi.")
        edit_test_handler(message, test_code)
        return

    try:
        new_name, new_answers = message.text.split('+')
        new_name = new_name.strip()
        new_answers = new_answers.strip().lower()
        update_test(test_code, new_answers, new_name)
        logger.info(f"User {message.chat.id} updated test {test_code}")
        bot.send_message(message.chat.id, f"✅ Test {test_code} muvaffaqiyatli yangilandi.")
        show_main_menu(message)
    except ValueError:
        bot.reply_to(message, "Xatolik yuz berdi. Iltimos, to'g'ri formatda kiriting.")
        edit_test_handler(message, test_code)

def show_test_statistics(message, test_code):
    test = get_test(test_code)
    if test:
        stats = get_test_statistics(test['id'])
        if stats:
            response = f"📊 Test {test_code} statistikasi:\n\n"
            for stat in stats:
                response += f"👤 Foydalanuvchi: {stat['name']} (@{stat['username']})\n"
                response += f"📞 Telefon: {stat['phone']}\n"
                response += f"🎯 Natija: {stat['score']:.2f}%\n"
                response += f"✅ Javoblari: {stat['user_answers']}\n"
                response += f"🕒 Topshirilgan vaqt: {stat['submitted_at']}\n"
                response += f"🔢 Urinishlar soni: {stat['attempt_count']}\n\n"
            
            excel_file = generate_excel_report(test_code, stats)
            
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("📥 Excel hisobotini yuklash", callback_data=f"download_excel_{test_code}"))
            keyboard.row(InlineKeyboardButton("🏠 Asosiy menyu", callback_data="main_menu"))
            
            bot.send_message(message.chat.id, response, reply_markup=keyboard)
            bot.send_document(message.chat.id, excel_file, caption=f"Test {test_code} natijalari")
        else:
            bot.send_message(message.chat.id, "Bu test hali ishlanmagan.")
    else:
        bot.send_message(message.chat.id, "Noto'g'ri test kodi.")

def add_scores_handler(message):
    bot.send_message(message.chat.id, 
    """
    ✅️ Testga ball qo'shish uchun 
    1.1;1.1;2.1.... ko'rinishida ballarni jo'nating. 
       
    ✅️ O'nli kasrni . bilan bering, orasi ; bilan bering. Oxiriga ; qo'ymang.

    ✅️ Barcha test uchun ball kiriting.
    """)
    bot.register_next_step_handler(message, process_add_scores)

def process_add_scores(message):
    if message.text is None:
        bot.reply_to(message, "Iltimos, matn formatida xabar yuboring. Rasm, stiker yoki boshqa turdagi xabarlar qabul qilinmaydi.")
        add_scores_handler(message)
        return

    try:
        scores = [float(score) for score in message.text.split(';')]
        test_code = get_latest_test_code(message.chat.id)
        if test_code:
            add_test_scores(test_code, scores)
            bot.send_message(message.chat.id, "✅ Ballar muvaffaqiyatli qo'shildi.")
        else:
            bot.send_message(message.chat.id, "❌ Sizning testingiz topilmadi.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Noto'g'ri format. Iltimos, qaytadan urinib ko'ring.")
    show_main_menu(message)

def get_latest_test_code(user_id):
    tests = get_user_tests(user_id)
    return tests[0]['code'] if tests else None

@subscription_required
def show_leaderboard(message):
    leaderboard = get_leaderboard()
    if leaderboard:
        response = "🏆 Top 10 foydalanuvchilar:\n\n"
        for i, user in enumerate(leaderboard, start=1):
            response += f"{i}. {user['name']} (@{user['username']})\n"
            response += f"   O'rtacha ball: {user['avg_score']:.2f}%\n"
            response += f"   Ishlangan testlar: {user['tests_taken']}\n\n"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("🏠 Asosiy menyu", callback_data="main_menu"))
        
        bot.send_message(message.chat.id, response, reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Hozircha reyting ma'lumotlari mavjud emas.")

@subscription_required
def help_handler(message):
    logger.info(f"User {message.chat.id} requested help")
    help_text = """
    🤖 Bot qo'llanmasi:
    
    /start - Botni ishga tushirish
    📝 Test yaratish - Yangi test yaratish
    🖍 Test ishlash - Mavjud testni ishlash
    📊 Testlarim - O'z testlaringizni ko'rish va tahrirlash
    🏆 Reyting - Eng yaxshi natijalarni ko'rish
    🆘 Yordam - Ushbu yordam xabarini ko'rsatish
    
    ❓ Agar muammolar yuzaga kelsa, @ablaze_coder yoki @Roziqulov_diyorbek  ga murojaat qiling.
    """
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("🏠 Asosiy menyu", callback_data="main_menu"))
    bot.send_message(message.chat.id, help_text, reply_markup=keyboard)

def show_admin_panel(message):
    if is_admin(message.from_user.id):
        keyboard = admin_menu_keyboard()
        bot.send_message(message.chat.id, "Admin panel:", reply_markup=keyboard)
    else:
        keyboard = admin_menu_keyboard()
        bot.send_message(message.chat.id, "Admin panel:", reply_markup=keyboard)

def admin_stats(message):
    user_count, test_count, result_count = get_user_stats()
    stats = f"📊 Statistika:\n\n"
    stats += f"👥 Jami foydalanuvchilar: {user_count}\n"
    stats += f"📝 Jami testlar: {test_count}\n"
    stats += f"🎯 Jami test natijalari: {result_count}\n"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📥 CSV yuklash", callback_data="admin_download_csv"))
    keyboard.row(InlineKeyboardButton("◀️ Orqaga", callback_data="admin_panel"))
    
    bot.send_message(message.chat.id, stats, reply_markup=keyboard)

def admin_broadcast(message):
    bot.send_message(message.chat.id, "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni kiriting:")
    bot.register_next_step_handler(message, process_admin_broadcast)

def process_admin_broadcast(message):
    if message.text is None:
        bot.reply_to(message, "Iltimos, matn formatida xabar yuboring. Rasm, stiker yoki boshqa turdagi xabarlar qabul qilinmaydi.")
        admin_broadcast(message)
        return

    broadcast_message = message.text
    user_ids = get_all_user_ids()
    success_count = 0
    for user_id in user_ids:
        try:
            bot.send_message(user_id, broadcast_message)
            success_count += 1
        except Exception as e:
            logger.error(f"Error sending broadcast to user {user_id}: {e}")
    
    bot.reply_to(message, f"Xabar {success_count}/{len(user_ids)} foydalanuvchiga yuborildi.")
    show_admin_panel(message)

def admin_users(message):
    users = get_all_users()
    user_list = "👥 Foydalanuvchilar ro'yxati (ilk 10 ta):\n\n"
    for user in users[:10]:  
        user_list += f"ID: {user['id']}, Ism: {user['name']}, Username: @{user['username']}\n"
    
    csv_data = generate_users_csv()
    csv_file = io.BytesIO(csv_data.encode())
    csv_file.name = 'users.csv'
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("◀️ Orqaga", callback_data="admin_panel"))
    
    bot.send_message(message.chat.id, user_list)
    bot.send_document(message.chat.id, csv_file, caption="To'liq foydalanuvchilar ro'yxati", reply_markup=keyboard)

def admin_search_test(message):
    bot.send_message(message.chat.id, "Qidirmoqchi bo'lgan test kodini yoki nomini kiriting:")
    bot.register_next_step_handler(message, process_admin_search_test)

def process_admin_search_test(message):
    if message.text is None:
        bot.reply_to(message, "Iltimos, matn formatida xabar yuboring. Rasm, stiker yoki boshqa turdagi xabarlar qabul qilinmaydi.")
        admin_search_test(message)
        return

    query = message.text.strip()
    tests = search_test(query)
    if tests:
        result = "🔍 Qidiruv natijalari:\n\n"
        for test in tests:
            result += f"Kod: {test['code']}, Nomi: {test['name']}, Yaratuvchi: {test['creator_name']}\n"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(InlineKeyboardButton("◀️ Orqaga", callback_data="admin_panel"))
        
        bot.send_message(message.chat.id, result, reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Ushbu so'rov bo'yicha testlar topilmadi.")
        admin_search_test(message)

def admin_delete_old_tests(message):
    bot.send_message(message.chat.id, "Necha kundan oldingi testlarni o'chirmoqchisiz? (Raqam kiriting)")
    bot.register_next_step_handler(message, process_admin_delete_old_tests)

def process_admin_delete_old_tests(message):
    if message.text is None:
        bot.reply_to(message, "Iltimos, matn formatida xabar yuboring. Rasm, stiker yoki boshqa turdagi xabarlar qabul qilinmaydi.")
        admin_delete_old_tests(message)
        return

    try:
        days = int(message.text)
        deleted_count = delete_old_tests(days)
        bot.send_message(message.chat.id, f"{deleted_count} ta test o'chirildi.")
    except ValueError:
        bot.send_message(message.chat.id, "Noto'g'ri format. Iltimos, raqam kiriting.")
    show_admin_panel(message)

def send_users_csv(message):
    csv_data = generate_users_csv()
    csv_file = io.StringIO(csv_data)
    csv_file.seek(0)
    bot.send_document(message.chat.id, ('users.csv', csv_file.getvalue().encode('utf-8')), caption="Foydalanuvchilar ro'yxati")

def cancel_operation(message):
    bot.send_message(message.chat.id, "Amal bekor qilindi.", reply_markup=main_menu_keyboard())

if __name__ == "__main__":
    logger.info("Bot started")
    bot.polling(none_stop=True)

