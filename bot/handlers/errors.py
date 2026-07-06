# bot/handlers/errors.py
"""
معالج الأخطاء المركزي
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import (
    TelegramError,
    NetworkError,
    TimedOut,
    BadRequest,
    Forbidden,
    RetryAfter
)
from ..utils.logger import logger
import traceback
import html
import json

class ErrorHandler:
    """معالج الأخطاء المركزي للتطبيق"""
    
    def __init__(self):
        self.error_counts = {}
    
    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        المعالج الرئيسي للأخطاء
        
        المعاملات:
            update: تحديث تيليجرام
            context: سياق التطبيق
        """
        try:
            # تسجيل الخطأ
            logger.error(
                f"استثناء أثناء معالجة تحديث: {context.error}",
                exc_info=context.error
            )
            
            # زيادة عداد الأخطاء
            error_type = type(context.error).__name__
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            
            # معالجة أنواع مختلفة من الأخطاء
            if isinstance(context.error, Forbidden):
                await self._handle_forbidden_error(update, context)
            
            elif isinstance(context.error, BadRequest):
                await self._handle_bad_request_error(update, context)
            
            elif isinstance(context.error, TimedOut):
                await self._handle_timeout_error(update, context)
            
            elif isinstance(context.error, NetworkError):
                await self._handle_network_error(update, context)
            
            elif isinstance(context.error, RetryAfter):
                await self._handle_retry_error(update, context)
            
            else:
                await self._handle_general_error(update, context)
            
            # إخطار المطور إذا كان الخطأ حرجاً
            if self._is_critical_error(context.error):
                await self._notify_developer(update, context)
            
        except Exception as e:
            logger.error(f"خطأ في معالج الأخطاء نفسه: {e}")
    
    async def _handle_forbidden_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أخطاء الصلاحيات (تم حظر البوت)"""
        if update and update.effective_user:
            user_id = update.effective_user.id
            logger.warning(f"البوت محظور من قبل المستخدم {user_id}")
            
            # يمكن إزالة المستخدم من قاعدة البيانات
            try:
                from ..database.crud import UserCRUD
                from ..database.database import get_db
                
                async for db in get_db():
                    user_crud = UserCRUD(db)
                    user = await user_crud.get_user(user_id)
                    if user:
                        user.status = "blocked"
                        await db.commit()
                        logger.info(f"تم تحديث حالة المستخدم {user_id} إلى محظور")
            except Exception as e:
                logger.error(f"خطأ في تحديث حالة المستخدم: {e}")
    
    async def _handle_bad_request_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أخطاء الطلب الخاطئ"""
        error_message = str(context.error)
        logger.warning(f"طلب خاطئ: {error_message}")
        
        if update and update.effective_message:
            language = context.user_data.get('language', 'ar') if context else 'ar'
            
            # رسائل مخصصة حسب نوع الخطأ
            if "message is not modified" in error_message:
                # تجاهل هذا الخطأ
                return
            
            elif "query is too old" in error_message:
                messages = {
                    'ar': "⏰ هذا الزر منتهي الصلاحية. الرجاء استخدام قائمة جديدة.",
                    'en': "⏰ This button has expired. Please use a fresh menu."
                }
            
            elif "message can't be deleted" in error_message:
                messages = {
                    'ar': "⚠️ لا يمكن حذف هذه الرسالة.",
                    'en': "⚠️ This message cannot be deleted."
                }
            
            elif "chat not found" in error_message:
                messages = {
                    'ar': "❌ المحادثة غير موجودة.",
                    'en': "❌ Chat not found."
                }
            
            else:
                messages = {
                    'ar': "❌ حدث خطأ في الطلب. الرجاء المحاولة مرة أخرى.",
                    'en': "❌ Bad request error. Please try again."
                }
            
            try:
                await update.effective_message.reply_text(
                    messages.get(language, messages['ar'])
                )
            except:
                pass
    
    async def _handle_timeout_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أخطاء انتهاء المهلة"""
        logger.warning("انتهت مهلة الطلب")
        
        if update and update.effective_message:
            language = context.user_data.get('language', 'ar') if context else 'ar'
            messages = {
                'ar': "⏰ انتهت مهلة الاتصال. جاري إعادة المحاولة...",
                'en': "⏰ Connection timeout. Retrying..."
            }
            try:
                await update.effective_message.reply_text(
                    messages.get(language, messages['ar'])
                )
            except:
                pass
    
    async def _handle_network_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أخطاء الشبكة"""
        logger.error(f"خطأ في الشبكة: {context.error}")
        
        # محاولة إعادة الاتصال
        if context and context.application:
            try:
                await context.application.initialize()
                logger.info("تمت إعادة تهيئة التطبيق بعد خطأ الشبكة")
            except Exception as e:
                logger.error(f"فشل في إعادة تهيئة التطبيق: {e}")
    
    async def _handle_retry_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أخطاء إعادة المحاولة (تحديد المعدل)"""
        if isinstance(context.error, RetryAfter):
            retry_after = context.error.retry_after
            logger.warning(f"تحديد المعدل: انتظر {retry_after} ثانية")
            
            if update and update.effective_message:
                language = context.user_data.get('language', 'ar') if context else 'ar'
                messages = {
                    'ar': f"⚠️ يرجى الانتظار {retry_after} ثانية قبل المحاولة مرة أخرى.",
                    'en': f"⚠️ Please wait {retry_after} seconds before trying again."
                }
                try:
                    await update.effective_message.reply_text(
                        messages.get(language, messages['ar'])
                    )
                except:
                    pass
    
    async def _handle_general_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الأخطاء العامة"""
        logger.error(f"خطأ غير متوقع: {context.error}")
        
        if update and update.effective_message:
            language = context.user_data.get('language', 'ar') if context else 'ar'
            
            # رسالة خطأ عامة
            messages = {
                'ar': (
                    "❌ عذراً، حدث خطأ غير متوقع.\n\n"
                    "🔄 جاري إصلاح المشكلة تلقائياً.\n"
                    "📝 يمكنك متابعة استخدام البوت.\n\n"
                    "إذا استمرت المشكلة، تواصل مع المطور."
                ),
                'en': (
                    "❌ Sorry, an unexpected error occurred.\n\n"
                    "🔄 The issue is being fixed automatically.\n"
                    "📝 You can continue using the bot.\n\n"
                    "If the problem persists, contact the developer."
                )
            }
            
            # إنشاء لوحة مفاتيح للعودة للقائمة
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 العودة للقائمة" if language == "ar" else "🔙 Back to Menu",
                    callback_data="main_menu"
                )]
            ])
            
            try:
                await update.effective_message.reply_text(
                    messages.get(language, messages['ar']),
                    reply_markup=keyboard
                )
            except:
                pass
    
    def _is_critical_error(self, error: Exception) -> bool:
        """تحديد ما إذا كان الخطأ حرجاً"""
        critical_errors = [
            "Can't parse entities",
            "Chat not found",
            "Bot was blocked",
            "USER_DEACTIVATED",
            "Unauthorized"
        ]
        
        error_str = str(error)
        return any(critical in error_str for critical in critical_errors)
    
    async def _notify_developer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إخطار المطور عن الأخطاء الحرجة"""
        try:
            from ..config import settings
            
            if settings.OWNER_ID:
                # تجميع معلومات الخطأ
                error_info = {
                    "error_type": type(context.error).__name__,
                    "error_message": str(context.error)[:500],
                    "update_data": str(update)[:500] if update else "No update",
                    "user_id": update.effective_user.id if update and update.effective_user else "Unknown",
                    "chat_id": update.effective_chat.id if update and update.effective_chat else "Unknown"
                }
                
                # تنسيق رسالة الإخطار
                notification = f"""
🚨 **تنبيه خطأ حرج**

**النوع:** {error_info['error_type']}
**الرسالة:** {html.escape(error_info['error_message'])}
**المستخدم:** {error_info['user_id']}
**المحادثة:** {error_info['chat_id']}

**التفاصيل الكاملة مسجلة في logs**
                """
                
                try:
                    await context.bot.send_message(
                        chat_id=settings.OWNER_ID,
                        text=notification,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"فشل في إرسال إخطار للمطور: {e}")
        
        except Exception as e:
            logger.error(f"خطأ في نظام الإخطار: {e}")
    
    async def get_error_statistics(self) -> dict:
        """الحصول على إحصائيات الأخطاء"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_types": self.error_counts,
            "critical_errors": sum(
                count for error_type, count in self.error_counts.items()
                if self._is_critical_error(Exception(error_type))
            )
        }
    
    async def reset_error_counts(self):
        """إعادة تعيين عدادات الأخطاء"""
        self.error_counts.clear()
        logger.info("تم إعادة تعيين عدادات الأخطاء")

# إنشاء مثيل عالمي من معالج الأخطاء
error_handler = ErrorHandler()

async def global_error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """الدالة العامة لمعالجة الأخطاء"""
    await error_handler.handle_error(update, context)
