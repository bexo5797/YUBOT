# ==================== ملف bot.py ====================
import os
import re
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# ==================== متغيرات البيئة ====================
TOKEN = os.getenv('BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))  # معرف الأدمن (رقمي)

if not TOKEN or not MONGO_URI or not ADMIN_ID:
    raise ValueError("❌ تأكد من تعيين BOT_TOKEN, MONGO_URI, ADMIN_ID")

# ==================== اتصال MongoDB ====================
client = MongoClient(MONGO_URI)
db = client['story_bot']
stories_col = db['stories']
users_col = db['users']
settings_col = db['settings']

# ==================== إعدادات البوت ====================
bot = telebot.TeleBot(TOKEN)

# دالة لجلب الإعدادات (القناة الإجبارية)
def get_channel():
    setting = settings_col.find_one({'_id': 'channel'})
    return setting['channel'] if setting else None

def set_channel(channel):
    settings_col.update_one(
        {'_id': 'channel'},
        {'$set': {'channel': channel}},
        upsert=True
    )

# ==================== دوال التحقق من الاشتراك ====================
def is_subscribed(user_id):
    channel = get_channel()
    if not channel:
        return True  # إذا لم يتم تعيين قناة، لا نحتاج تحقق
    
    try:
        member = bot.get_chat_member(channel, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def check_subscription_required(func):
    """ديكوراتور للتحقق من الاشتراك قبل تنفيذ الأمر"""
    def wrapper(message):
        user_id = message.from_user.id
        
        # الأدمن يستثنى من التحقق
        if user_id == ADMIN_ID:
            return func(message)
        
        if not is_subscribed(user_id):
            channel = get_channel()
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}"))
            markup.add(InlineKeyboardButton("✅ تأكد من الاشتراك", callback_data="check_subscription"))
            
            bot.reply_to(
                message,
                f"⚠️ للوصول إلى البوت، يجب الاشتراك في القناة أولاً:\n{channel}",
                reply_markup=markup
            )
            return
        
        return func(message)
    return wrapper

# ==================== دوال القصص ====================
def save_story_to_db(title, text, admin_id):
    stories_col.update_one(
        {'title': title},
        {'$set': {
            'title': title,
            'text': text,
            'admin_id': admin_id,
            'created_at': telebot.util.datetime.now()
        }},
        upsert=True
    )

def get_all_stories():
    return list(stories_col.find({}, {'_id': 0, 'title': 1, 'text': 1}))

def get_story(title):
    return stories_col.find_one({'title': title}, {'_id': 0, 'text': 1})

def delete_story(title):
    stories_col.delete_one({'title': title})

# ==================== تسجيل المستخدمين ====================
def register_user(user_id, username=None):
    users_col.update_one(
        {'user_id': user_id},
        {'$set': {
            'user_id': user_id,
            'username': username,
            'last_active': telebot.util.datetime.now()
        }},
        upsert=True
    )

# ==================== لوحة الأدمن ====================
def admin_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ قصة جديدة", callback_data="new_story"),
        InlineKeyboardButton("📝 تعديل قصة", callback_data="edit_story")
    )
    markup.add(
        InlineKeyboardButton("🗑 حذف قصة", callback_data="delete_story"),
        InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")
    )
    markup.add(
        InlineKeyboardButton("📢 تعيين قناة إجبارية", callback_data="set_channel"),
        InlineKeyboardButton("❌ إلغاء القناة", callback_data="remove_channel")
    )
    markup.add(
        InlineKeyboardButton("📋 عرض القصص", callback_data="list_stories")
    )
    return markup

# ==================== أوامر البوت ====================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    register_user(user_id, message.from_user.username)
    
    # التحقق من الاشتراك للمستخدمين العاديين
    if user_id != ADMIN_ID and not is_subscribed(user_id):
        channel = get_channel()
        if channel:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}"))
            markup.add(InlineKeyboardButton("✅ تأكد من الاشتراك", callback_data="check_subscription"))
            
            bot.reply_to(
                message,
                f"👋 أهلاً بك!\n\n⚠️ للوصول إلى القصص، اشترك في القناة أولاً:\n{channel}",
                reply_markup=markup
            )
            return
    
    if user_id == ADMIN_ID:
        bot.reply_to(
            message,
            "👋 مرحباً أيها الأدمن!\n\n📌 استخدم /admin للوحة التحكم.",
            reply_markup=admin_keyboard()
        )
    else:
        show_stories_list(message.chat.id)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ هذا الأمر مخصص للأدمن فقط.")
        return
    
    bot.reply_to(
        message,
        "🔐 *لوحة تحكم الأدمن*\nاختر الإجراء المناسب:",
        reply_markup=admin_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['stories'])
@check_subscription_required
def list_stories_command(message):
    show_stories_list(message.chat.id)

# ==================== عرض القصص ====================
def show_stories_list(chat_id):
    stories = get_all_stories()
    if not stories:
        bot.send_message(chat_id, "📭 لا توجد قصص حالياً.")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for story in stories:
        buttons.append(InlineKeyboardButton(
            f"📖 {story['title']}",
            callback_data=f"story_{story['title']}"
        ))
    markup.add(*buttons)
    
    bot.send_message(chat_id, "📚 *جميع القصص المتاحة:*", reply_markup=markup, parse_mode='Markdown')

# ==================== كولباك الأدمن ====================
@bot.callback_query_handler(func=lambda call: call.data == "new_story")
def new_story(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ هذا الإجراء للأدمن فقط!")
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📝 ارسل *عنوان القصة*:")
    bot.register_next_step_handler(msg, save_title)

def save_title(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    title = message.text.strip()
    if not title:
        bot.reply_to(message, "❌ العنوان لا يمكن أن يكون فارغاً.")
        return
    
    # التحقق من وجود القصة
    if get_story(title):
        bot.reply_to(message, f"⚠️ قصة باسم '{title}' موجودة بالفعل!")
        return
    
    chat_id = message.chat.id
    bot.send_message(chat_id, f"✅ تم حفظ العنوان: *{title}*\nالآن ارسل *نص القصة*:", parse_mode='Markdown')
    bot.register_next_step_handler(message, lambda m: save_story_text(m, title))

def save_story_text(message, title):
    if message.from_user.id != ADMIN_ID:
        return
    
    text = message.text.strip()
    if not text:
        bot.reply_to(message, "❌ النص لا يمكن أن يكون فارغاً.")
        return
    
    # حفظ في MongoDB
    save_story_to_db(title, text, message.from_user.id)
    
    bot.reply_to(message, f"✅ تم حفظ القصة *{title}* بنجاح!", parse_mode='Markdown')
    show_stories_list(message.chat.id)

# ==================== حذف قصة ====================
@bot.callback_query_handler(func=lambda call: call.data == "delete_story")
def delete_story_menu(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ للأدمن فقط!")
        return
    
    stories = get_all_stories()
    if not stories:
        bot.answer_callback_query(call.id, "📭 لا توجد قصص للحذف")
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    for story in stories:
        markup.add(InlineKeyboardButton(
            f"🗑 {story['title']}",
            callback_data=f"confirm_delete_{story['title']}"
        ))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin"))
    
    bot.edit_message_text(
        "🗑 *اختر القصة للحذف:*",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_"))
def confirm_delete(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ للأدمن فقط!")
        return
    
    title = call.data.replace("confirm_delete_", "")
    delete_story(title)
    
    bot.answer_callback_query(call.id, f"✅ تم حذف '{title}'")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_stories_list(call.message.chat.id)

# ==================== تعيين القناة الإجبارية ====================
@bot.callback_query_handler(func=lambda call: call.data == "set_channel")
def set_channel_command(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ للأدمن فقط!")
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📢 ارسل معرف القناة (مع @ أو بدون):\nمثال: @my_channel"
    )
    bot.register_next_step_handler(msg, save_channel)

def save_channel(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    channel = message.text.strip()
    # تنظيف المعرف
    if not channel.startswith('@'):
        channel = f'@{channel}'
    
    set_channel(channel)
    bot.reply_to(message, f"✅ تم تعيين القناة الإجبارية: {channel}")

@bot.callback_query_handler(func=lambda call: call.data == "remove_channel")
def remove_channel(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ للأدمن فقط!")
        return
    
    set_channel(None)
    bot.answer_callback_query(call.id, "✅ تم إلغاء القناة الإجبارية")
    bot.edit_message_text(
        "✅ تم إلغاء الاشتراك الإجباري.",
        call.message.chat.id,
        call.message.message_id
    )

# ==================== التحقق من الاشتراك ====================
@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_sub(call):
    user_id = call.from_user.id
    channel = get_channel()
    
    if not channel:
        bot.answer_callback_query(call.id, "✅ لا يوجد قناة إجبارية حالياً")
        show_stories_list(call.message.chat.id)
        return
    
    try:
        member = bot.get_chat_member(channel, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            bot.answer_callback_query(call.id, "✅ تم التحقق! مرحباً بك 🎉")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_stories_list(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, "❌ لم تشترك بعد، اشترك ثم اضغط تأكد")
    except:
        bot.answer_callback_query(call.id, "❌ حدث خطأ، حاول مجدداً")

# ==================== عرض الإحصائيات ====================
@bot.callback_query_handler(func=lambda call: call.data == "stats")
def show_stats(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ للأدمن فقط!")
        return
    
    total_stories = stories_col.count_documents({})
    total_users = users_col.count_documents({})
    channel = get_channel()
    
    stats_text = f"""
📊 *الإحصائيات:*

📚 عدد القصص: {total_stories}
👥 عدد المستخدمين: {total_users}
📢 القناة الإجبارية: {channel if channel else '❌ لا توجد'}

🆔 معرف الأدمن: `{ADMIN_ID}`
    """
    
    bot.edit_message_text(
        stats_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")
        )
    )

# ==================== عرض القصص للأدمن ====================
@bot.callback_query_handler(func=lambda call: call.data == "list_stories")
def admin_list_stories(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ للأدمن فقط!")
        return
    
    show_stories_list(call.message.chat.id)

# ==================== رجوع للوحة الأدمن ====================
@bot.callback_query_handler(func=lambda call: call.data == "back_to_admin")
def back_to_admin(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ للأدمن فقط!")
        return
    
    bot.edit_message_text(
        "🔐 *لوحة تحكم الأدمن*\nاختر الإجراء المناسب:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=admin_keyboard(),
        parse_mode='Markdown'
    )

# ==================== عرض القصة ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("story_"))
@check_subscription_required
def send_story(call):
    title = call.data.replace("story_", "")
    story = get_story(title)
    
    if story:
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            f"📖 *{title}*\n\n{story['text']}",
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(call.id, "❌ القصة غير موجودة")

# ==================== تشغيل البوت ====================
if __name__ == "__main__":
    print("✅ البوت يعمل مع MongoDB...")
    print(f"👤 الأدمن: {ADMIN_ID}")
    print(f"📢 القناة: {get_channel() or 'لا توجد'}")
    bot.infinity_polling()
