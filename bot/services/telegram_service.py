# bot/services/telegram_service.py
"""
خدمة التفاعل مع تيليجرام API
"""
from typing import Optional, Dict, Any, List
from telegram import Bot, InputFile
from telegram.error import TelegramError
from ..utils.logger import logger
from ..config import settings
import aiofiles
import os
from pathlib import Path

class TelegramService:
    """خدمة تيليجرام المساعدة"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.temp_dir = Path("data/temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_file(
        self,
        file_id: str,
        file_type: str = "photo"
    ) -> Optional[bytes]:
        """
        تحميل ملف من تيليجرام
        
        المعاملات:
            file_id: معرف الملف
            file_type: نوع الملف
            
        المخرجات:
            بيانات الملف
        """
        try:
            # الحصول على معلومات الملف
            file = await self.bot.get_file(file_id)
            
            # تحميل الملف
            file_bytes = await file.download_as_bytearray()
            return bytes(file_bytes)
            
        except Exception as e:
            logger.error(f"خطأ في تحميل الملف: {e}")
            return None
    
    async def send_file(
        self,
        chat_id: int,
        file_path: str,
        file_type: str = "document",
        caption: Optional[str] = None
    ) -> bool:
        """
        إرسال ملف إلى المستخدم
        
        المعاملات:
            chat_id: معرف المحادثة
            file_path: مسار الملف
            file_type: نوع الملف
            caption: وصف الملف
            
        المخرجات:
            نجاح العملية
        """
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                file_data = await f.read()
            
            if file_type == "photo":
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=file_data,
                    caption=caption
                )
            elif file_type == "video":
                await self.bot.send_video(
                    chat_id=chat_id,
                    video=file_data,
                    caption=caption
                )
            elif file_type == "sticker":
                await self.bot.send_sticker(
                    chat_id=chat_id,
                    sticker=file_data
                )
            else:
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=file_data,
                    caption=caption
                )
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إرسال الملف: {e}")
            return False
    
    async def broadcast_message(
        self,
        user_ids: List[int],
        message: str,
        photo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        إرسال رسالة جماعية للمستخدمين
        
        المعاملات:
            user_ids: قائمة معرفات المستخدمين
            message: نص الرسالة
            photo: مسار الصورة (اختياري)
            
        المخرجات:
            إحصائيات الإرسال
        """
        success_count = 0
        fail_count = 0
        
        for user_id in user_ids:
            try:
                if photo and os.path.exists(photo):
                    await self.bot.send_photo(
                        chat_id=user_id,
                        photo=open(photo, 'rb'),
                        caption=message
                    )
                else:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=message
                    )
                success_count += 1
                
            except TelegramError as e:
                logger.warning(f"فشل إرسال رسالة إلى {user_id}: {e}")
                fail_count += 1
            
            except Exception as e:
                logger.error(f"خطأ في البث إلى {user_id}: {e}")
                fail_count += 1
        
        return {
            "total": len(user_ids),
            "success": success_count,
            "failed": fail_count
        }
    
    async def check_bot_permissions(self) -> Dict[str, bool]:
        """
        التحقق من صلاحيات البوت
        
        المخرجات:
            قاموس الصلاحيات
        """
        try:
            bot_info = await self.bot.get_me()
            return {
                "can_join_groups": bot_info.can_join_groups,
                "can_read_all_group_messages": bot_info.can_read_all_group_messages,
                "supports_inline_queries": bot_info.supports_inline_queries
            }
        except Exception as e:
            logger.error(f"خطأ في التحقق من صلاحيات البوت: {e}")
            return {}
    
    async def get_sticker_set_info(
        self,
        set_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        الحصول على معلومات مجموعة ملصقات
        
        المعاملات:
            set_name: اسم المجموعة
            
        المخرجات:
            معلومات المجموعة
        """
        try:
            sticker_set = await self.bot.get_sticker_set(set_name)
            
            return {
                "name": sticker_set.name,
                "title": sticker_set.title,
                "is_animated": sticker_set.is_animated,
                "is_video": sticker_set.is_video,
                "sticker_count": len(sticker_set.stickers),
                "stickers": [
                    {
                        "file_id": s.file_id,
                        "file_unique_id": s.file_unique_id,
                        "emoji": s.emoji,
                        "file_size": s.file_size
                    }
                    for s in sticker_set.stickers[:10]  # أول 10 ملصقات
                ]
            }
            
        except TelegramError as e:
            logger.error(f"خطأ في الحصول على معلومات مجموعة الملصقات: {e}")
            return None
    
    async def validate_sticker_file(
        self,
        file_id: str,
        sticker_type: str = "static"
    ) -> Tuple[bool, str]:
        """
        التحقق من صحة ملف الملصق
        
        المعاملات:
            file_id: معرف الملف
            sticker_type: نوع الملصق (static, animated, video)
            
        المخرجات:
            (صالح, رسالة)
        """
        try:
            file = await self.bot.get_file(file_id)
            
            if not file:
                return False, "الملف غير موجود"
            
            # التحقق من حجم الملف
            if file.file_size:
                if sticker_type == "static" and file.file_size > 512 * 1024:
                    return False, "حجم الملف كبير جداً (الحد الأقصى 512 كيلوبايت)"
                elif sticker_type in ["animated", "video"] and file.file_size > 256 * 1024:
                    return False, "حجم الملف كبير جداً (الحد الأقصى 256 كيلوبايت)"
            
            # التحقق من الأبعاد
            if file.file_path:
                if sticker_type == "static":
                    # التحقق من أبعاد PNG
                    if not file.file_path.endswith('.png'):
                        return False, "الملصق العادي يجب أن يكون بصيغة PNG"
            
            return True, "الملف صالح"
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من صحة الملصق: {e}")
            return False, str(e)
