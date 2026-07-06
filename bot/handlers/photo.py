# bot/handlers/photo.py
"""
معالج الصور
"""
from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from ..services.sticker_service import StickerService
from ..services.image_service import ImageService
from ..utils.decorators import handle_errors, require_registration, rate_limit
from ..utils.validators import FileValidator
from ..utils.logger import logger
from ..utils.helpers import validate_emoji
from ..keyboards.inline import InlineKeyboards
from ..database.crud import UserCRUD
from ..database.database import get_db
import os
import aiofiles

@handle_errors
@require_registration
@rate_limit
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استقبال الصور"""
    user_id = update.effective_user.id
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    # الحصول على أكبر صورة
    photo = update.message.photo[-1]
    file_id = photo.file_id
    file_size = photo.file_size if hasattr(photo, 'file_size') else 0
    
    # التحقق من حجم الصورة
    if file_size > 10 * 1024 * 1024:  # 10MB
        messages = {
            'ar': "❌ حجم الصورة كبير جداً. الحد الأقصى 10 ميجابايت",
            'en': "❌ Photo size is too large. Maximum size is 10MB"
        }
        await update.message.reply_text(messages[language])
        return
    
    # إرسال رسالة انتظار
    wait_messages = {
        'ar': "⏳ جاري معالجة الصورة...",
        'en': "⏳ Processing photo..."
    }
    processing_msg = await update.message.reply_text(wait_messages[language])
    
    try:
        # تحميل الصورة
        bot = context.bot
        file = await bot.get_file(file_id)
        photo_bytes = await file.download_as_bytearray()
        
        # إنشاء خدمة الملصقات
        sticker_service = StickerService(bot)
        
        # تحويل الصورة لملصق
        file_id, message = await sticker_service.create_sticker_from_photo(
            bytes(photo_bytes),
            user_id,
            emoji="⭐"
        )
        
        if file_id:
            # إرسال الملصق
            await update.message.reply_sticker(
                sticker=file_id,
                reply_to_message_id=update.message.message_id
            )
            
            # طلب الإيموجي
            emoji_messages = {
                'ar': "✅ تم إنشاء الملصق! أرسل الإيموجي المناسب لهذا الملصق",
                'en': "✅ Sticker created! Send the appropriate emoji for this sticker"
            }
            
            # حفظ file_id في context لاستخدامه لاحقاً
            context.user_data['last_sticker_file_id'] = file_id
            context.user_data['awaiting_emoji'] = True
            
            await processing_msg.edit_text(
                emoji_messages[language],
                reply_markup=InlineKeyboards.emoji_selection(language)
            )
        else:
            await processing_msg.edit_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"خطأ في معالجة الصورة: {e}")
        error_messages = {
            'ar': "❌ حدث خطأ أثناء معالجة الصورة. يرجى المحاولة مرة أخرى.",
            'en': "❌ An error occurred while processing the photo. Please try again."
        }
        await processing_msg.edit_text(error_messages[language])

@handle_errors
@require_registration
async def handle_emoji_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استقبال الإيموجي للملصق"""
    user_id = update.effective_user.id
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    # التحقق من وجود ملصق سابق
    if not context.user_data.get('awaiting_emoji'):
        return
    
    # التحقق من صحة الإيموجي
    text = update.message.text.strip()
    is_valid, emoji_or_msg = validate_emoji(text)
    
    if not is_valid:
        messages = {
            'ar': f"❌ {emoji_or_msg}\nالرجاء إرسال إيموجي واحد فقط.",
            'en': f"❌ {emoji_or_msg}\nPlease send only one emoji."
        }
        await update.message.reply_text(messages[language])
        return
    
    # حفظ الإيموجي
    context.user_data['last_emoji'] = emoji_or_msg
    context.user_data['awaiting_emoji'] = False
    
    # سؤال المستخدم عن الحزمة
    success_messages = {
        'ar': f"✅ تم تعيين الإيموجي: {emoji_or_msg}\n\nهل تريد إضافة هذا الملصق إلى حزمة موجودة؟\nأرسل اسم الحزمة أو اضغط /skip للتخطي",
        'en': f"✅ Emoji set: {emoji_or_msg}\n\nDo you want to add this sticker to an existing pack?\nSend pack name or press /skip to skip"
    }
    
    await update.message.reply_text(
        success_messages[language],
        reply_markup=InlineKeyboards.main_menu(language)
    )

@handle_errors
@require_registration
async def handle_photo_for_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج إضافة صورة مباشرة إلى حزمة"""
    user_id = update.effective_user.id
    
    # التحقق من وجود حزمة محددة
    pack_name = context.user_data.get('current_pack')
    if not pack_name:
        return
    
    # معالجة الصورة
    await handle_photo(update, context)

# تسجيل المعالجات
photo_handler = MessageHandler(filters.PHOTO, handle_photo)
emoji_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_emoji_selection)
