# bot/services/pack_service.py
"""
خدمة إدارة حزم الملصقات
"""
from typing import Optional, Tuple, List, Dict, Any
from telegram import Bot
from telegram.error import TelegramError
from ..utils.logger import logger
from ..utils.helpers import sanitize_pack_name, generate_unique_id, generate_pack_share_link
from ..database.crud import PackCRUD, UserCRUD, StickerCRUD
from ..database.database import get_db
from ..database.models import PackType

class PackService:
    """خدمة إدارة حزم الملصقات"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.max_packs_per_user = 50
        self.max_stickers_per_pack = 120
    
    async def create_pack(
        self,
        user_id: int,
        pack_name: str,
        pack_title: str,
        pack_type: PackType = PackType.STATIC,
        first_sticker: Optional[str] = None,
        emoji: str = "⭐"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        إنشاء حزمة ملصقات جديدة
        
        المعاملات:
            user_id: معرف المستخدم
            pack_name: اسم الحزمة (بالأحرف الإنجليزية)
            pack_title: عنوان الحزمة (للقراءة)
            pack_type: نوع الحزمة
            first_sticker: file_id للملصق الأول
            emoji: الإيموجي
            
        المخرجات:
            (نجاح, رسالة, رابط_المشاركة)
        """
        try:
            # تنظيف اسم الحزمة
            clean_name = sanitize_pack_name(pack_name)
            if not clean_name:
                return False, "اسم الحزمة غير صالح", None
            
            # إضافة لاحقة اسم البوت
            full_pack_name = f"{clean_name}_by_{self.bot.username}"
            
            # التحقق من عدم وجود الحزمة مسبقاً
            async for db in get_db():
                pack_crud = PackCRUD(db)
                existing_pack = await pack_crud.get_pack(full_pack_name)
                if existing_pack:
                    return False, "يوجد حزمة بهذا الاسم بالفعل", None
                
                # التحقق من عدد حزم المستخدم
                user_packs_count = await pack_crud.get_user_packs_count(user_id)
                if user_packs_count >= self.max_packs_per_user:
                    return False, f"لقد وصلت للحد الأقصى من الحزم ({self.max_packs_per_user} حزمة)", None
            
            # إنشاء الحزمة في تيليجرام
            if pack_type == PackType.STATIC:
                result = await self.bot.create_new_sticker_set(
                    user_id=user_id,
                    name=full_pack_name,
                    title=pack_title[:64],
                    emojis=emoji,
                    png_sticker=first_sticker if first_sticker else None
                )
            elif pack_type == PackType.ANIMATED:
                result = await self.bot.create_new_sticker_set(
                    user_id=user_id,
                    name=full_pack_name,
                    title=pack_title[:64],
                    emojis=emoji,
                    tgs_sticker=first_sticker if first_sticker else None
                )
            else:
                result = await self.bot.create_new_sticker_set(
                    user_id=user_id,
                    name=full_pack_name,
                    title=pack_title[:64],
                    emojis=emoji,
                    webm_sticker=first_sticker if first_sticker else None
                )
            
            if result:
                # حفظ في قاعدة البيانات
                async for db in get_db():
                    pack_crud = PackCRUD(db)
                    pack = await pack_crud.create_pack(
                        user_id=user_id,
                        pack_name=full_pack_name,
                        pack_title=pack_title[:64],
                        pack_type=pack_type
                    )
                    
                    if first_sticker:
                        sticker_crud = StickerCRUD(db)
                        await sticker_crud.add_sticker(
                            pack_id=pack.id,
                            file_id=first_sticker,
                            file_unique_id=f"{full_pack_name}_first",
                            emoji=emoji
                        )
                
                share_link = generate_pack_share_link(full_pack_name)
                return True, f"تم إنشاء الحزمة بنجاح: {pack_title}", share_link
            
            return False, "فشل في إنشاء الحزمة", None
            
        except TelegramError as e:
            error_msg = str(e)
            if "NAME_NOT_OCCUPIED" in error_msg:
                return False, "اسم الحزمة غير متاح", None
            elif "STICKERSET_INVALID" in error_msg:
                return False, "الملصق غير صالح", None
            elif "PACK_SHORT_NAME_OCCUPIED" in error_msg:
                return False, "اسم الحزمة محجوز بالفعل", None
            elif "STICKERS_TOO_MUCH" in error_msg:
                return False, "لقد تجاوزت الحد المسموح من الملصقات", None
            else:
                logger.error(f"خطأ تيليجرام في إنشاء الحزمة: {e}")
                return False, f"خطأ: {str(e)[:100]}", None
        except Exception as e:
            logger.error(f"خطأ في إنشاء الحزمة: {e}")
            return False, str(e), None
    
    async def delete_pack(
        self,
        user_id: int,
        pack_name: str
    ) -> Tuple[bool, str]:
        """
        حذف حزمة ملصقات
        
        المعاملات:
            user_id: معرف المستخدم
            pack_name: اسم الحزمة
            
        المخرجات:
            (نجاح, رسالة)
        """
        try:
            # حذف من قاعدة البيانات أولاً
            async for db in get_db():
                pack_crud = PackCRUD(db)
                pack = await pack_crud.get_pack(pack_name)
                
                if not pack:
                    return False, "الحزمة غير موجودة"
                
                if pack.user_id != user_id:
                    return False, "ليس لديك صلاحية حذف هذه الحزمة"
                
                # حذف من تيليجرام
                try:
                    await self.bot.delete_sticker_set(pack_name)
                except TelegramError as e:
                    logger.warning(f"خطأ في حذف الحزمة من تيليجرام: {e}")
                
                # حذف من قاعدة البيانات
                await pack_crud.delete_pack(pack_name)
                
                return True, "تم حذف الحزمة بنجاح"
            
            return False, "خطأ في حذف الحزمة"
            
        except Exception as e:
            logger.error(f"خطأ في حذف الحزمة: {e}")
            return False, str(e)
    
    async def get_user_packs(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        الحصول على حزم المستخدم
        
        المعاملات:
            user_id: معرف المستخدم
            limit: عدد النتائج
            offset: الإزاحة
            
        المخرجات:
            قائمة الحزم
        """
        try:
            async for db in get_db():
                pack_crud = PackCRUD(db)
                packs = await pack_crud.get_user_packs(user_id, limit, offset)
                
                result = []
                for pack in packs:
                    share_link = generate_pack_share_link(pack.pack_name)
                    result.append({
                        "id": pack.id,
                        "name": pack.pack_name,
                        "title": pack.pack_title,
                        "type": pack.pack_type.value if pack.pack_type else "static",
                        "sticker_count": pack.sticker_count,
                        "created_at": pack.created_at,
                        "share_link": share_link
                    })
                
                return result
            
            return []
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على حزم المستخدم: {e}")
            return []
    
    async def get_pack_info(
        self,
        pack_name: str,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        الحصول على معلومات الحزمة
        
        المعاملات:
            pack_name: اسم الحزمة
            user_id: معرف المستخدم (للتحقق من الملكية)
            
        المخرجات:
            معلومات الحزمة
        """
        try:
            async for db in get_db():
                pack_crud = PackCRUD(db)
                pack = await pack_crud.get_pack(pack_name)
                
                if not pack:
                    return None
                
                if user_id and pack.user_id != user_id:
                    return None
                
                sticker_crud = StickerCRUD(db)
                stickers = await sticker_crud.get_pack_stickers(pack.id)
                
                share_link = generate_pack_share_link(pack.pack_name)
                
                return {
                    "id": pack.id,
                    "name": pack.pack_name,
                    "title": pack.pack_title,
                    "type": pack.pack_type.value if pack.pack_type else "static",
                    "sticker_count": pack.sticker_count,
                    "created_at": pack.created_at,
                    "share_link": share_link,
                    "stickers": [
                        {
                            "file_id": s.file_id,
                            "emoji": s.emoji,
                            "position": s.position
                        }
                        for s in stickers
                    ]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات الحزمة: {e}")
            return None
    
    async def rename_pack(
        self,
        user_id: int,
        pack_name: str,
        new_title: str
    ) -> Tuple[bool, str]:
        """
        إعادة تسمية حزمة (تغيير العنوان فقط)
        
        المعاملات:
            user_id: معرف المستخدم
            pack_name: اسم الحزمة الحالي
            new_title: العنوان الجديد
            
        المخرجات:
            (نجاح, رسالة)
        """
        try:
            # التحقق من الملكية
            async for db in get_db():
                pack_crud = PackCRUD(db)
                pack = await pack_crud.get_pack(pack_name)
                
                if not pack:
                    return False, "الحزمة غير موجودة"
                
                if pack.user_id != user_id:
                    return False, "ليس لديك صلاحية تعديل هذه الحزمة"
                
                # تحديث العنوان في تيليجرام
                try:
                    await self.bot.set_sticker_set_title(
                        name=pack_name,
                        title=new_title[:64]
                    )
                except TelegramError as e:
                    logger.error(f"خطأ في تحديث عنوان الحزمة: {e}")
                    return False, "فشل في تحديث عنوان الحزمة"
                
                # تحديث في قاعدة البيانات
                await pack_crud.update_pack(pack_name, pack_title=new_title[:64])
                
                return True, "تم تحديث عنوان الحزمة بنجاح"
            
            return False, "خطأ في تحديث الحزمة"
            
        except Exception as e:
            logger.error(f"خطأ في إعادة تسمية الحزمة: {e}")
            return False, str(e)
    
    async def add_sticker_to_existing_pack(
        self,
        user_id: int,
        pack_name: str,
        sticker_file_id: str,
        emoji: str
    ) -> Tuple[bool, str]:
        """
        إضافة ملصق إلى حزمة موجودة
        
        المعاملات:
            user_id: معرف المستخدم
            pack_name: اسم الحزمة
            sticker_file_id: file_id للملصق
            emoji: الإيموجي
            
        المخرجات:
            (نجاح, رسالة)
        """
        try:
            # التحقق من الحزمة
            async for db in get_db():
                pack_crud = PackCRUD(db)
                pack = await pack_crud.get_pack(pack_name)
                
                if not pack:
                    return False, "الحزمة غير موجودة"
                
                if pack.user_id != user_id:
                    return False, "ليس لديك صلاحية إضافة ملصقات لهذه الحزمة"
                
                if pack.sticker_count >= self.max_stickers_per_pack:
                    return False, f"الحزمة ممتلئة (الحد الأقصى {self.max_stickers_per_pack} ملصق)"
                
                # إضافة الملصق في تيليجرام
                try:
                    await self.bot.add_sticker_to_set(
                        user_id=user_id,
                        name=pack_name,
                        sticker=sticker_file_id,
                        emojis=emoji
                    )
                except TelegramError as e:
                    error_msg = str(e)
                    if "STICKERSET_INVALID" in error_msg:
                        return False, "الملصق غير صالح أو غير متوافق مع نوع الحزمة"
                    elif "STICKERS_TOO_MUCH" in error_msg:
                        return False, "الحزمة ممتلئة"
                    else:
                        logger.error(f"خطأ في إضافة ملصق: {e}")
                        return False, f"فشل في إضافة الملصق: {str(e)[:100]}"
                
                # حفظ في قاعدة البيانات
                sticker_crud = StickerCRUD(db)
                await sticker_crud.add_sticker(
                    pack_id=pack.id,
                    file_id=sticker_file_id,
                    file_unique_id=f"{pack_name}_{sticker_file_id}_{pack.sticker_count}",
                    emoji=emoji
                )
                
                return True, f"تمت إضافة الملصق إلى الحزمة ({pack.sticker_count + 1}/{self.max_stickers_per_pack})"
            
            return False, "خطأ في إضافة الملصق"
            
        except Exception as e:
            logger.error(f"خطأ في إضافة ملصق إلى حزمة: {e}")
            return False, str(e)
    
    async def remove_sticker_from_pack(
        self,
        user_id: int,
        pack_name: str,
        sticker_file_id: str
    ) -> Tuple[bool, str]:
        """
        حذف ملصق من حزمة
        
        المعاملات:
            user_id: معرف المستخدم
            pack_name: اسم الحزمة
            sticker_file_id: file_id للملصق
            
        المخرجات:
            (نجاح, رسالة)
        """
        try:
            async for db in get_db():
                pack_crud = PackCRUD(db)
                pack = await pack_crud.get_pack(pack_name)
                
                if not pack:
                    return False, "الحزمة غير موجودة"
                
                if pack.user_id != user_id:
                    return False, "ليس لديك صلاحية حذف ملصقات من هذه الحزمة"
                
                # حذف من تيليجرام
                try:
                    await self.bot.delete_sticker_from_set(sticker_file_id)
                except TelegramError as e:
                    logger.error(f"خطأ في حذف الملصق من تيليجرام: {e}")
                    return False, "فشل في حذف الملصق"
                
                # حذف من قاعدة البيانات
                sticker_crud = StickerCRUD(db)
                sticker = await sticker_crud.get_sticker(
                    f"{pack_name}_{sticker_file_id}_"
                )
                if sticker:
                    await sticker_crud.delete_sticker(sticker.id)
                
                return True, "تم حذف الملصق بنجاح"
            
            return False, "خطأ في حذف الملصق"
            
        except Exception as e:
            logger.error(f"خطأ في حذف ملصق من حزمة: {e}")
            return False, str(e)
    
    async def get_pack_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        الحصول على إحصائيات الحزم للمستخدم
        
        المعاملات:
            user_id: معرف المستخدم
            
        المخرجات:
            الإحصائيات
        """
        try:
            async for db in get_db():
                pack_crud = PackCRUD(db)
                user_crud = UserCRUD(db)
                
                packs = await pack_crud.get_user_packs(user_id)
                
                total_stickers = sum(pack.sticker_count for pack in packs)
                static_packs = sum(1 for p in packs if p.pack_type == PackType.STATIC)
                animated_packs = sum(1 for p in packs if p.pack_type == PackType.ANIMATED)
                
                return {
                    "total_packs": len(packs),
                    "total_stickers": total_stickers,
                    "static_packs": static_packs,
                    "animated_packs": animated_packs,
                    "packs": [
                        {
                            "name": p.pack_name,
                            "title": p.pack_title,
                            "stickers": p.sticker_count,
                            "type": p.pack_type.value if p.pack_type else "static",
                            "share_link": generate_pack_share_link(p.pack_name)
                        }
                        for p in packs[:10]  # أحدث 10 حزم
                    ]
                }
            
            return {"total_packs": 0, "total_stickers": 0}
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على إحصائيات الحزم: {e}")
            return {"total_packs": 0, "total_stickers": 0}
