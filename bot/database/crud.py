# bot/database/crud.py
"""
عمليات قاعدة البيانات (CRUD)
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .models import User, StickerPack, Sticker, Log, UserState, UserStatus, PackType
from ..utils.logger import logger
import json
from datetime import datetime

class UserCRUD:
    """عمليات المستخدمين"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        language: str = "ar"
    ) -> User:
        """إنشاء مستخدم جديد"""
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            language=language
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        logger.info(f"تم إنشاء مستخدم جديد: {user_id}")
        return user
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """الحصول على مستخدم بواسطة ID"""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_or_create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> User:
        """الحصول على مستخدم أو إنشائه"""
        user = await self.get_user(user_id)
        if not user:
            user = await self.create_user(user_id, username, first_name)
        else:
            # تحديث المعلومات
            if username and username != user.username:
                user.username = username
            if first_name and first_name != user.first_name:
                user.first_name = first_name
            await self.db.flush()
        return user
    
    async def update_language(self, user_id: int, language: str) -> bool:
        """تحديث لغة المستخدم"""
        user = await self.get_user(user_id)
        if user:
            user.language = language
            await self.db.flush()
            return True
        return False
    
    async def update_user_stats(self, user_id: int, packs_delta: int = 0, stickers_delta: int = 0):
        """تحديث إحصائيات المستخدم"""
        user = await self.get_user(user_id)
        if user:
            user.total_packs += packs_delta
            user.total_stickers += stickers_delta
            await self.db.flush()
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """الحصول على إحصائيات المستخدم"""
        user = await self.get_user(user_id)
        if user:
            return {
                "total_packs": user.total_packs,
                "total_stickers": user.total_stickers,
                "language": user.language,
                "created_at": user.created_at
            }
        return {}
    
    async def get_all_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """الحصول على جميع المستخدمين"""
        result = await self.db.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def get_users_count(self) -> int:
        """الحصول على عدد المستخدمين"""
        result = await self.db.execute(
            select(func.count(User.id))
        )
        return result.scalar() or 0

class PackCRUD:
    """عمليات حزم الملصقات"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_pack(
        self,
        user_id: int,
        pack_name: str,
        pack_title: str,
        pack_type: PackType = PackType.STATIC
    ) -> StickerPack:
        """إنشاء حزمة ملصقات جديدة"""
        pack = StickerPack(
            user_id=user_id,
            pack_name=pack_name,
            pack_title=pack_title,
            pack_type=pack_type
        )
        self.db.add(pack)
        await self.db.flush()
        await self.db.refresh(pack)
        
        # تحديث إحصائيات المستخدم
        user_crud = UserCRUD(self.db)
        await user_crud.update_user_stats(user_id, packs_delta=1)
        
        logger.info(f"تم إنشاء حزمة ملصقات: {pack_name} بواسطة {user_id}")
        return pack
    
    async def get_pack(self, pack_name: str) -> Optional[StickerPack]:
        """الحصول على حزمة بواسطة الاسم"""
        result = await self.db.execute(
            select(StickerPack).where(StickerPack.pack_name == pack_name)
        )
        return result.scalar_one_or_none()
    
    async def get_pack_by_id(self, pack_id: int) -> Optional[StickerPack]:
        """الحصول على حزمة بواسطة ID"""
        result = await self.db.execute(
            select(StickerPack).where(StickerPack.id == pack_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_packs(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[StickerPack]:
        """الحصول على حزم المستخدم"""
        result = await self.db.execute(
            select(StickerPack)
            .where(StickerPack.user_id == user_id)
            .order_by(StickerPack.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def get_user_packs_count(self, user_id: int) -> int:
        """الحصول على عدد حزم المستخدم"""
        result = await self.db.execute(
            select(func.count(StickerPack.id))
            .where(StickerPack.user_id == user_id)
        )
        return result.scalar() or 0
    
    async def update_pack(
        self,
        pack_name: str,
        **kwargs
    ) -> Optional[StickerPack]:
        """تحديث حزمة"""
        pack = await self.get_pack(pack_name)
        if pack:
            for key, value in kwargs.items():
                if hasattr(pack, key):
                    setattr(pack, key, value)
            await self.db.flush()
            await self.db.refresh(pack)
        return pack
    
    async def delete_pack(self, pack_name: str) -> bool:
        """حذف حزمة"""
        pack = await self.get_pack(pack_name)
        if pack:
            # حذف الملصقات المرتبطة
            await self.db.execute(
                delete(Sticker).where(Sticker.pack_id == pack.id)
            )
            # تحديث إحصائيات المستخدم
            user_crud = UserCRUD(self.db)
            await user_crud.update_user_stats(
                pack.user_id,
                packs_delta=-1,
                stickers_delta=-pack.sticker_count
            )
            # حذف الحزمة
            await self.db.delete(pack)
            await self.db.flush()
            logger.info(f"تم حذف حزمة الملصقات: {pack_name}")
            return True
        return False
    
    async def get_total_packs_count(self) -> int:
        """الحصول على العدد الإجمالي للحزم"""
        result = await self.db.execute(
            select(func.count(StickerPack.id))
        )
        return result.scalar() or 0

class StickerCRUD:
    """عمليات الملصقات"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def add_sticker(
        self,
        pack_id: int,
        file_id: str,
        file_unique_id: str,
        emoji: str,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None
    ) -> Sticker:
        """إضافة ملصق إلى حزمة"""
        # الحصول على الموضع التالي
        result = await self.db.execute(
            select(func.count(Sticker.id))
            .where(Sticker.pack_id == pack_id)
        )
        position = result.scalar() or 0
        
        sticker = Sticker(
            pack_id=pack_id,
            file_id=file_id,
            file_unique_id=file_unique_id,
            emoji=emoji,
            position=position,
            file_size=file_size,
            mime_type=mime_type
        )
        self.db.add(sticker)
        
        # تحديث عدد الملصقات في الحزمة
        pack_crud = PackCRUD(self.db)
        pack = await pack_crud.get_pack_by_id(pack_id)
        if pack:
            pack.sticker_count = position + 1
            # تحديث إحصائيات المستخدم
            user_crud = UserCRUD(self.db)
            await user_crud.update_user_stats(pack.user_id, stickers_delta=1)
        
        await self.db.flush()
        await self.db.refresh(sticker)
        logger.info(f"تمت إضافة ملصق إلى الحزمة {pack_id}")
        return sticker
    
    async def get_sticker(self, file_unique_id: str) -> Optional[Sticker]:
        """الحصول على ملصق بواسطة معرف فريد"""
        result = await self.db.execute(
            select(Sticker).where(Sticker.file_unique_id == file_unique_id)
        )
        return result.scalar_one_or_none()
    
    async def get_pack_stickers(
        self,
        pack_id: int,
        limit: int = 120,
        offset: int = 0
    ) -> List[Sticker]:
        """الحصول على ملصقات الحزمة"""
        result = await self.db.execute(
            select(Sticker)
            .where(Sticker.pack_id == pack_id)
            .order_by(Sticker.position.asc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def delete_sticker(self, sticker_id: int) -> bool:
        """حذف ملصق"""
        sticker = await self.db.get(Sticker, sticker_id)
        if sticker:
            pack_id = sticker.pack_id
            await self.db.delete(sticker)
            
            # تحديث عدد الملصقات
            pack_crud = PackCRUD(self.db)
            pack = await pack_crud.get_pack_by_id(pack_id)
            if pack:
                pack.sticker_count -= 1
                user_crud = UserCRUD(self.db)
                await user_crud.update_user_stats(pack.user_id, stickers_delta=-1)
            
            await self.db.flush()
            return True
        return False
    
    async def update_sticker_position(
        self,
        sticker_id: int,
        new_position: int
    ) -> bool:
        """تحديث موضع الملصق"""
        sticker = await self.db.get(Sticker, sticker_id)
        if sticker:
            sticker.position = new_position
            await self.db.flush()
            return True
        return False

class LogCRUD:
    """عمليات السجلات"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def add_log(
        self,
        user_id: Optional[int],
        action: str,
        details: Optional[str] = None,
        level: str = "INFO"
    ) -> Log:
        """إضافة سجل جديد"""
        log = Log(
            user_id=user_id,
            action=action,
            details=details,
            level=level
        )
        self.db.add(log)
        await self.db.flush()
        return log
    
    async def get_user_logs(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Log]:
        """الحصول على سجلات المستخدم"""
        result = await self.db.execute(
            select(Log)
            .where(Log.user_id == user_id)
            .order_by(Log.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

class StateCRUD:
    """عمليات حالة المستخدم"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def set_state(
        self,
        user_id: int,
        state: str,
        data: Optional[Dict] = None
    ):
        """تعيين حالة المستخدم"""
        result = await self.db.execute(
            select(UserState).where(UserState.user_id == user_id)
        )
        user_state = result.scalar_one_or_none()
        
        if user_state:
            user_state.state = state
            user_state.data = json.dumps(data) if data else None
            user_state.updated_at = datetime.now()
        else:
            user_state = UserState(
                user_id=user_id,
                state=state,
                data=json.dumps(data) if data else None
            )
            self.db.add(user_state)
        
        await self.db.flush()
    
    async def get_state(self, user_id: int) -> Optional[Dict]:
        """الحصول على حالة المستخدم"""
        result = await self.db.execute(
            select(UserState).where(UserState.user_id == user_id)
        )
        user_state = result.scalar_one_or_none()
        
        if user_state:
            return {
                "state": user_state.state,
                "data": json.loads(user_state.data) if user_state.data else None
            }
        return None
    
    async def clear_state(self, user_id: int):
        """مسح حالة المستخدم"""
        await self.db.execute(
            delete(UserState).where(UserState.user_id == user_id)
        )
        await self.db.flush()
