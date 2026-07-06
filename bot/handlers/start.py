# bot/handlers/start.py
"""
معالج أمر البدء
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, ContextTypes
from ..keyboards.inline import InlineKeyboards
from ..keyboards.reply import ReplyKeyboards
from ..utils.decorators import handle_errors, require_registration
from ..utils.logger import logger
from ..database.crud import UserCRUD
from ..database.database import get_db

@handle_errors
@require_registration
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user = update.effective_user
    user_id = user.id
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    # رسالة الترحيب حسب اللغة
    if language == "ar":
        welcome_message = f"""
🌟 **مرحباً بك في بوت الملصقات الاحترافي!** 🌟

أهلاً {user.first_name}!

أنا بوت متخصص في إنشاء وإدارة ملصقات تيليجرام. يمكنني مساعدتك في:

🖼 **تحويل الصور لملصقات**
• أرسل أي صورة وسأحولها لملصق
• دعم الخلفيات الشفافة
• تحسين الجودة تلقائياً

🎥 **تحويل الفيديو لملصقات متحركة**
• أرسل فيديو قصير (حتى 3 ثواني)
• تحويل تلقائي للملصقات المتحركة

📦 **إدارة حزم الملصقات**
• إنشاء حزم ملصقات جديدة
• إضافة وحذف الملصقات
• مشاركة الحزم مع الأصدقاء

⚙️ **الإعدادات**
• دعم اللغتين العربية والإنجليزية
• إحصائيات مفصلة

---
اختر من القائمة أدناه للبدء:
        """
    else:
        welcome_message = f"""
🌟 **Welcome to the Professional Sticker Bot!** 🌟

Hello {user.first_name}!

I'm a specialized bot for creating and managing Telegram stickers. I can help you with:

🖼 **Convert Photos to Stickers**
• Send any photo and I'll convert it to a sticker
• Transparent background support
• Automatic quality optimization

🎥 **Convert Videos to Animated Stickers**
• Send short videos (up to 3 seconds)
• Automatic conversion to animated stickers

📦 **Manage Sticker Packs**
• Create new sticker packs
• Add and remove stickers
• Share packs with friends

⚙️ **Settings**
• Arabic and English language support
• Detailed statistics

---
Choose from the menu below to get started:
        """
    
    # إرسال الرسالة مع لوحة المفاتيح
    await update.message.reply_text(
        welcome_message,
        reply_markup=InlineKeyboards.main_menu(language),
        parse_mode='Markdown'
    )
    
    # إرسال لوحة المفاتيح العادية
    await update.message.reply_text(
        "اختر من القائمة" if language == "ar" else "Choose from menu",
        reply_markup=ReplyKeyboards.main_keyboard(language)
    )
    
    logger.info(f"المستخدم {user_id} بدأ البوت")

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر تغيير اللغة"""
    await update.message.reply_text(
        "اختر اللغة / Choose language:",
        reply_markup=InlineKeyboards.language_selection()
    )

# تسجيل المعالجات
start_handler = CommandHandler('start', start_command)
language_handler = CommandHandler('language', language_command)
