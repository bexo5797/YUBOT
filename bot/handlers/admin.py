# bot/handlers/admin.py
"""
معالج أوامر المشرف
"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from ..utils.decorators import handle_errors, admin_only
from ..utils.logger import logger
from ..config import settings
from ..keyboards.inline import InlineKeyboards
from ..services.telegram_service import TelegramService
from ..database.crud import UserCRUD, PackCRUD, LogCRUD
from ..database.database import get_db
from typing import List

@handle_errors
@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """المعالج الرئيسي لأوامر المشرف"""
    user_id = update.effective_user.id
    language = context.user_data.get('language', 'ar')
    
    if language == "ar":
        text = """
👑 **لوحة تحكم المشرف**

الأوامر المتاحة:
/admin - عرض هذه القائمة
/admin_stats - إحصائيات البوت
/admin_users - قائمة المستخدمين
/admin_broadcast - إرسال رسالة للجميع
/admin_packs - إدارة الحزم
        """
    else:
        text = """
👑 **Admin Control Panel**

Available commands:
/admin - Show this menu
/admin_stats - Bot statistics
/admin_users - Users list
/admin_broadcast - Send broadcast
/admin_packs - Manage packs
        """
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboards.admin_menu(language),
        parse_mode='Markdown'
    )

@handle_errors
@admin_only
async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج إحصائيات المشرف"""
    async for db in get_db():
        user_crud = UserCRUD(db)
        pack_crud = PackCRUD(db)
        
        total_users = await user_crud.get_users_count()
        total_packs = await pack_crud.get_total_packs_count()
        
        language = context.user_data.get('language', 'ar')
        
        if language == "ar":
            text = f"""
📊 **إحصائيات البوت**

👥 عدد المستخدمين: {total_users}
📦 عدد الحزم: {total_packs}
🤖 حالة البوت: {'يعمل ✅' if context.bot else 'متوقف ❌'}
🖥 وضع التشغيل: {'Webhook' if settings.WEBHOOK_URL else 'Polling'}
            """
        else:
            text = f"""
📊 **Bot Statistics**

👥 Total Users: {total_users}
📦 Total Packs: {total_packs}
🤖 Bot Status: {'Running ✅' if context.bot else 'Stopped ❌'}
🖥 Running Mode: {'Webhook' if settings.WEBHOOK_URL else 'Polling'}
            """
        
        await update.message.reply_text(text, parse_mode='Markdown')

@handle_errors
@admin_only
async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج عرض المستخدمين"""
    async for db in get_db():
        user_crud = UserCRUD(db)
        users = await user_crud.get_all_users(limit=20)
        
        language = context.user_data.get('language', 'ar')
        
        if not users:
            text = "لا يوجد مستخدمين" if language == "ar" else "No users found"
            await update.message.reply_text(text)
            return
        
        if language == "ar":
            text = "👥 **آخر 20 مستخدم:**\n\n"
            for user in users:
                text += f"• `{user.user_id}` - {user.first_name or 'غير معروف'}\n"
                text += f"  ├ الحزم: {user.total_packs}\n"
                text += f"  └ اللغة: {user.language}\n\n"
        else:
            text = "👥 **Last 20 Users:**\n\n"
            for user in users:
                text += f"• `{user.user_id}` - {user.first_name or 'Unknown'}\n"
                text += f"  ├ Packs: {user.total_packs}\n"
                text += f"  └ Language: {user.language}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')

@handle_errors
@admin_only
async def admin_broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج البث للمستخدمين"""
    language = context.user_data.get('language', 'ar')
    
    if not context.args:
        if language == "ar":
            text = "الرجاء إرسال الرسالة مع الأمر:\n/admin_broadcast [الرسالة]"
        else:
            text = "Please send the message with the command:\n/admin_broadcast [message]"
        await update.message.reply_text(text)
        return
    
    message_text = ' '.join(context.args)
    
    # إرسال رسالة تأكيد
    if language == "ar":
        confirm_text = f"سيتم إرسال الرسالة التالية لجميع المستخدمين:\n\n{message_text}\n\nهل أنت متأكد؟"
    else:
        confirm_text = f"The following message will be sent to all users:\n\n{message_text}\n\nAre you sure?"
    
    context.user_data['broadcast_message'] = message_text
    await update.message.reply_text(
        confirm_text,
        reply_markup=InlineKeyboards.confirmation_keyboard("broadcast", language)
    )

@handle_errors
@admin_only
async def admin_packs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج إدارة الحزم (مشرف)"""
    async for db in get_db():
        pack_crud = PackCRUD(db)
        packs = await pack_crud.get_user_packs(0, limit=20)  # جميع الحزم
        
        language = context.user_data.get('language', 'ar')
        
        if not packs:
            text = "لا توجد حزم" if language == "ar" else "No packs found"
            await update.message.reply_text(text)
            return
        
        if language == "ar":
            text = "📦 **جميع الحزم:**\n\n"
            for pack in packs:
                text += f"• {pack.pack_title} ({pack.pack_name})\n"
                text += f"  ├ المالك: {pack.user_id}\n"
                text += f"  └ الملصقات: {pack.sticker_count}\n\n"
        else:
            text = "📦 **All Packs:**\n\n"
            for pack in packs:
                text += f"• {pack.pack_title} ({pack.pack_name})\n"
                text += f"  ├ Owner: {pack.user_id}\n"
                text += f"  └ Stickers: {pack.sticker_count}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')

# تسجيل معالجات المشرف
admin_handler = CommandHandler('admin', admin_command)
admin_stats_handler = CommandHandler('admin_stats', admin_stats_command)
admin_users_handler = CommandHandler('admin_users', admin_users_command)
admin_broadcast_handler = CommandHandler('admin_broadcast', admin_broadcast_command)
admin_packs_handler = CommandHandler('admin_packs', admin_packs_command)
