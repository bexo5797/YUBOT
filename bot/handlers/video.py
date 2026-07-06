# bot/handlers/video.py
"""
معالج الفيديو
"""
from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from ..services.sticker_service import StickerService
from ..services.video_service import VideoService
from ..utils.decorators import handle_errors, require_registration, rate_limit
from ..utils.validators import FileValidator
from ..utils.logger import logger
from ..keyboards.inline import InlineKeyboards
from ..database.crud import UserCRUD
from ..database.database import get_db

@handle_errors
@require_registration
@rate_limit
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استقبال الفيديو"""
    user_id = update.effective_user.id
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    video = update.message.video or update.message.animation
    
    if not video:
        messages = {
            'ar': "❌ الرجاء إرسال فيديو أو GIF",
            'en': "❌ Please send a video or GIF"
        }
        await update.message.reply_text(messages[language])
        return
    
    # التحقق من المدة
    duration = video.duration
    if duration > 3:
        messages = {
            'ar': f"❌ مدة الفيديو طويلة جداً ({duration} ثانية). الحد الأقصى 3 ثواني.",
            'en': f"❌ Video duration is too long ({duration} seconds). Maximum is 3 seconds."
        }
        await update.message.reply_text(messages[language])
        return
    
    # التحقق من الحجم
    file_size = video.file_size if hasattr(video, 'file_size') else 0
    if file_size > 50 * 1024 * 1024:  # 50MB
        messages = {
            'ar': "❌ حجم الفيديو كبير جداً. الحد الأقصى 50 ميجابايت",
            'en': "❌ Video size is too large. Maximum size is 50MB"
        }
        await update.message.reply_text(messages[language])
        return
    
    # إرسال رسالة انتظار
    wait_messages = {
        'ar': "⏳ جاري معالجة الفيديو... هذه العملية قد تستغرق بعض الوقت",
        'en': "⏳ Processing video... This may take some time"
    }
    processing_msg = await update.message.reply_text(wait_messages[language])
    
    try:
        # تحميل الفيديو
        bot = context.bot
        file = await bot.get_file(video.file_id)
        video_bytes = await file.download_as_bytearray()
        
        # إنشاء خدمة الملصقات
        sticker_service = StickerService(bot)
        
        # تحويل الفيديو لملصق متحرك
        file_id, message = await sticker_service.create_animated_sticker_from_video(
            bytes(video_bytes),
            user_id,
            emoji="⭐"
        )
        
        if file_id:
            # إرسال الملصق المتحرك
            await update.message.reply_sticker(
                sticker=file_id,
                reply_to_message_id=update.message.message_id
            )
            
            # حفظ file_id في context
            context.user_data['last_sticker_file_id'] = file_id
            context.user_data['awaiting_emoji'] = True
            context.user_data['sticker_type'] = 'animated'
            
            success_messages = {
                'ar': "✅ تم إنشاء الملصق المتحرك! أرسل الإيموجي المناسب",
                'en': "✅ Animated sticker created! Send the appropriate emoji"
            }
            
            await processing_msg.edit_text(
                success_messages[language],
                reply_markup=InlineKeyboards.emoji_selection(language)
            )
        else:
            await processing_msg.edit_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"خطأ في معالجة الفيديو: {e}")
        error_messages = {
            'ar': "❌ حدث خطأ أثناء معالجة الفيديو. تأكد من تثبيت FFmpeg",
            'en': "❌ An error occurred while processing video. Make sure FFmpeg is installed"
        }
        await processing_msg.edit_text(error_messages[language])

@handle_errors
@require_registration
async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج ملفات GIF"""
    # معالجة GIF كفيديو
    await handle_video(update, context)

# تسجيل المعالجات
video_handler = MessageHandler(filters.VIDEO, handle_video)
animation_handler = MessageHandler(filters.ANIMATION, handle_gif)
