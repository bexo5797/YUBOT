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
            'en': "❌ Please send a
