# bot/utils/decorators.py
"""
زخارف للتطبيق
"""
import asyncio
from functools import wraps
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes
from .logger import logger
from .validators import rate_limiter

def handle_errors(func: Callable) -> Callable:
    """زخرفة لمعالجة الأخطاء بشكل مركزي"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"خطأ في {func.__name__}: {e}", exc_info=True)
            
            # إرسال رسالة خطأ للمستخدم
            if update and update.effective_message:
                error_messages = {
                    'ar': "❌ عذراً، حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى لاحقاً.",
                    'en': "❌ Sorry, an unexpected error occurred. Please try again later."
                }
                lang = context.user_data.get('language', 'ar') if context else 'ar'
                await update.effective_message.reply_text(
                    error_messages.get(lang, error_messages['ar'])
                )
    return wrapper

def rate_limit(func: Callable) -> Callable:
    """زخرفة لتحديد معدل الطلبات"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update and update.effective_user:
            user_id = update.effective_user.id
            
            if not rate_limiter.is_allowed(user_id):
                lang = context.user_data.get('language', 'ar')
                messages = {
                    'ar': "⚠️ يرجى الانتظار قليلاً قبل إرسال طلب آخر.",
                    'en': "⚠️ Please wait a moment before sending another request."
                }
                await update.effective_message.reply_text(
                    messages.get(lang, messages['ar'])
                )
                return
            
            return await func(update, context, *args, **kwargs)
        return await func(update, context, *args, **kwargs)
    return wrapper

def admin_only(func: Callable) -> Callable:
    """زخرفة لتقييد الوصول للمشرفين فقط"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from ..config import settings
        
        if update and update.effective_user:
            user_id = update.effective_user.id
            
            if user_id != settings.OWNER_ID:
                lang = context.user_data.get('language', 'ar')
                messages = {
                    'ar': "⛔ عذراً، هذا الأمر متاح للمشرفين فقط.",
                    'en': "⛔ Sorry, this command is for admins only."
                }
                await update.effective_message.reply_text(
                    messages.get(lang, messages['ar'])
                )
                return
            
            return await func(update, context, *args, **kwargs)
        return await func(update, context, *args, **kwargs)
    return wrapper

def require_registration(func: Callable) -> Callable:
    """زخرفة للتأكد من تسجيل المستخدم"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from ..database.crud import UserCRUD
        from ..database.database import get_db
        
        if update and update.effective_user:
            user_id = update.effective_user.id
            
            async for db in get_db():
                user_crud = UserCRUD(db)
                user = await user_crud.get_user(user_id)
                
                if not user:
                    # تسجيل المستخدم تلقائياً
                    user = await user_crud.create_user(
                        user_id=user_id,
                        username=update.effective_user.username,
                        first_name=update.effective_user.first_name,
                        language='ar'
                    )
            
            return await func(update, context, *args, **kwargs)
        return await func(update, context, *args, **kwargs)
    return wrapper
