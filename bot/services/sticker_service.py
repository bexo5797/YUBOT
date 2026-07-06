# bot/services/sticker_service.py
"""
خدمة الملصقات - معالجة وإنشاء الملصقات
"""
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import os
import aiofiles
from telegram import Bot
from ..utils.logger import logger
from ..database.crud import StickerCRUD, PackCRUD, UserCRUD
from ..database.database import get_db
from .image_service import ImageService
from .video_service import VideoService

class StickerService:
    """خدمة إدارة الملصقات"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.temp_dir = Path("data/temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_sticker_from_photo(
        self,
        photo_file: bytes,
        user_id: int,
        emoji: str = "⭐"
    ) -> Tuple[Optional[str], str]:
        """
        إنشاء ملصق من صورة
        
        المعاملات:
            photo_file: بيانات الصورة
            user_id: معرف المستخدم
            emoji: الإيموجي المرتبط
            
        المخرجات:
            (file_id, رسالة)
        """
        temp_input = None
        temp_output = None
        
        try:
            # حفظ الصورة مؤقتاً
            temp_input = self.temp_dir / f"input_{user_id}_{os.urandom(4).hex()}.jpg"
            temp_output = self.temp_dir / f"output_{user_id}_{os.urandom(4).hex()}.webp"
            
            async with aiofiles.open(temp_input, 'wb') as f:
                await f.write(photo_file)
            
            # معالجة الصورة
            success, msg = await ImageService.process_image(
                str(temp_input),
                str(temp_output)
            )
            
            if not success:
                return None, msg
            
            # إرسال الملصق إلى تيليجرام للحصول على file_id
            async with aiofiles.open(temp_output, 'rb') as f:
                sticker_data = await f.read()
            
            # إرسال كملصق
            sent_sticker = await self.bot.send_sticker(
                chat_id=user_id,
                sticker=sticker_data
            )
            
            if sent_sticker and sent_sticker.sticker:
                return sent_sticker.sticker.file_id, "تم إنشاء الملصق بنجاح"
            
            return None, "فشل في إنشاء الملصق"
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء ملصق من صورة: {e}")
            return None, str(e)
        
        finally:
            # تنظيف الملفات المؤقتة
            if temp_input and temp_input.exists():
                temp_input.unlink()
            if temp_output and temp_output.exists():
                temp_output.unlink()
    
    async def create_animated_sticker_from_video(
        self,
        video_file: bytes,
        user_id: int,
        emoji: str = "⭐"
    ) -> Tuple[Optional[str], str]:
        """
        إنشاء ملصق متحرك من فيديو
        
        المعاملات:
            video_file: بيانات الفيديو
            user_id: معرف المستخدم
            emoji: الإيموجي المرتبط
            
        المخرجات:
            (file_id, رسالة)
        """
        temp_input = None
        temp_output = None
        
        try:
            # حفظ الفيديو مؤقتاً
            temp_input = self.temp_dir / f"input_{user_id}_{os.urandom(4).hex()}.mp4"
            temp_output = self.temp_dir / f"output_{user_id}_{os.urandom(4).hex()}.webm"
            
            async with aiofiles.open(temp_input, 'wb') as f:
                await f.write(video_file)
            
            # معالجة الفيديو
            success, msg = await VideoService.process_video(
                str(temp_input),
                str(temp_output)
            )
            
            if not success:
                return None, msg
            
            # إرسال الملصق المتحرك
            async with aiofiles.open(temp_output, 'rb') as f:
                sticker_data = await f.read()
            
            sent_sticker = await self.bot.send_sticker(
                chat_id=user_id,
                sticker=sticker_data
            )
            
            if sent_sticker and sent_sticker.sticker:
                return sent_sticker.sticker.file_id, "تم إنشاء الملصق المتحرك بنجاح"
            
            return None, "فشل في إنشاء الملصق المتحرك"
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء ملصق متحرك: {e}")
            return None, str(e)
        
        finally:
            # تنظيف الملفات المؤقتة
            if temp_input and temp_input.exists():
                temp_input.unlink()
            if temp_output and temp_output.exists():
                temp_output.unlink()
    
    async def add_sticker_to_pack(
        self,
        user_id: int,
        pack_name: str,
        file_id: str,
        emoji: str
    ) -> Tuple[bool, str]:
        """
        إضافة ملصق إلى حزمة موجودة
        
        المعاملات:
            user_id: معرف المستخدم
            pack_name: اسم الحزمة
            file_id: معرف الملف
            emoji: الإيموجي
            
        المخرجات:
            (نجاح, رسالة)
        """
        try:
            # إضافة الملصق إلى حزمة تيليجرام
            result = await self.bot.add_sticker_to_set(
                user_id=user_id,
                name=pack_name,
                sticker=file_id,
                emojis=emoji
            )
            
            if result:
                # حفظ في قاعدة البيانات
                async for db in get_db():
                    sticker_crud = StickerCRUD(db)
                    pack_crud = PackCRUD(db)
                    
                    pack = await pack_crud.get_pack(pack_name)
                    if pack:
                        await sticker_crud.add_sticker(
                            pack_id=pack.id,
                            file_id=file_id,
                            file_unique_id=f"{pack_name}_{file_id}",
                            emoji=emoji
                        )
                
                return True, "تمت إضافة الملصق إلى الحزمة"
            
            return False, "فشل في إضافة الملصق"
            
        except Exception as e:
            logger.error(f"خطأ في إضافة ملصق إلى حزمة: {e}")
            return False, str(e)
