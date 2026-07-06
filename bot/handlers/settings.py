# bot/handlers/settings.py
"""
معالج الإعدادات
"""
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from ..utils.decorators import handle_errors, require_registration
from ..utils.logger import logger
from ..keyboards.inline import InlineKeyboards
from ..database.crud import UserCRUD
from ..database.database import get_db

@handle_errors
@require_registration
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر الإعدادات"""
    user_id = update.effective_user.id
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    if language == "ar":
        text = """
⚙️ **الإعدادات**

يمكنك تخصيص إعدادات البوت من هنا:

🌐 **اللغة**: تغيير لغة البوت
🔔 **الإشعارات**: تفعيل أو تعطيل الإشعارات
📊 **الإحصائيات**: عرض إحصائيات استخدامك

اختر من القائمة أدناه:
        """
    else:
        text = """
⚙️ **Settings**

You can customize bot settings here:

🌐 **Language**: Change bot language
🔔 **Notifications**: Enable or disable notifications
📊 **Statistics**: View your usage statistics

Choose from the menu below:
        """
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboards.settings_menu(language),
        parse_mode='Markdown'
    )

@handle_errors
@require_registration
async def statistics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر الإحصائيات"""
    user_id = update.effective_user.id
    
    async for db in get_db():
        user_crud = UserCRUD(db)
        pack_crud = PackCRUD(db)
        
        stats = await user_crud.get_user_stats(user_id)
        packs_count = await pack_crud.get_user_packs_count(user_id)
        
        language = stats.get('language', 'ar')
        
        if language == "ar":
            text = f"""
📊 **إحصائياتك**

👤 **معلومات الحساب:**
• معرف المستخدم: `{user_id}`
• تاريخ التسجيل: {stats.get('created_at', 'غير معروف')}

📦 **الملصقات والحزم:**
• عدد الحزم: {packs_count}
• عدد الملصقات: {stats.get('total_stickers', 0)}

⚙️ **الإعدادات:**
• اللغة: {'العربية 🇸🇦' if stats.get('language') == 'ar' else 'English 🇬🇧'}
• الإشعارات: {'مفعلة ✅' if stats.get('notifications_enabled', True) else 'معطلة ❌'}
            """
        else:
            text = f"""
📊 **Your Statistics**

👤 **Account Info:**
• User ID: `{user_id}`
• Joined: {stats.get('created_at', 'Unknown')}

📦 **Stickers & Packs:**
• Packs: {packs_count}
• Stickers: {stats.get('total_stickers', 0)}

⚙️ **Settings:**
• Language: {'Arabic 🇸🇦' if stats.get('language') == 'ar' else 'English 🇬🇧'}
• Notifications: {'Enabled ✅' if stats.get('notifications_enabled', True) else 'Disabled ❌'}
            """
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboards.main_menu(language),
            parse_mode='Markdown'
        )

@handle_errors
@require_registration
async def toggle_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج تبديل حالة الإشعارات"""
    user_id = update.effective_user.id
    
    async for db in get_db():
        user_crud = UserCRUD(db)
        user = await user_crud.get_user(user_id)
        
        if user:
            user.notifications_enabled = not user.notifications_enabled
            await db.commit()
            
            language = user.language
            
            if user.notifications_enabled:
                text = "✅ تم تفعيل الإشعارات" if language == "ar" else "✅ Notifications enabled"
            else:
                text = "❌ تم تعطيل الإشعارات" if language == "ar" else "❌ Notifications disabled"
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboards.settings_menu(language)
            )

# تسجيل المعالجات
settings_handler = CommandHandler('settings', settings_command)
statistics_handler = CommandHandler('statistics', statistics_command)
notifications_handler = CommandHandler('notifications', toggle_notifications)
