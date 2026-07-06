# bot/database/models.py
"""
نماذج قاعدة البيانات
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, 
    DateTime, ForeignKey, Text, Enum, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class UserStatus(enum.Enum):
    """حالة المستخدم"""
    ACTIVE = "active"
    BLOCKED = "blocked"
    BANNED = "banned"

class PackType(enum.Enum):
    """نوع حزمة الملصقات"""
    STATIC = "static"
    ANIMATED = "animated"
    VIDEO = "video"

class User(Base):
    """جدول المستخدمين"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(32), nullable=True)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    language = Column(String(2), default="ar")
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    
    # إحصائيات
    total_stickers = Column(Integer, default=0)
    total_packs = Column(Integer, default=0)
    
    # الإعدادات
    notifications_enabled = Column(Boolean, default=True)
    auto_convert = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # العلاقات
    packs = relationship("StickerPack", back_populates="user", lazy="dynamic")
    logs = relationship("Log", back_populates="user", lazy="dynamic")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>"

class StickerPack(Base):
    """جدول حزم الملصقات"""
    __tablename__ = "sticker_packs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    pack_name = Column(String(64), unique=True, nullable=False, index=True)
    pack_title = Column(String(64), nullable=False)
    pack_type = Column(Enum(PackType), default=PackType.STATIC)
    
    # معلومات إضافية
    description = Column(String(256), nullable=True)
    is_public = Column(Boolean, default=True)
    sticker_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # العلاقات
    user = relationship("User", back_populates="packs")
    stickers = relationship("Sticker", back_populates="pack", lazy="dynamic")
    
    def __repr__(self):
        return f"<StickerPack(name={self.pack_name}, title={self.pack_title})>"

class Sticker(Base):
    """جدول الملصقات"""
    __tablename__ = "stickers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pack_id = Column(Integer, ForeignKey("sticker_packs.id"), nullable=False)
    file_id = Column(String(256), nullable=False)
    file_unique_id = Column(String(256), unique=True, nullable=False)
    
    # معلومات الملصق
    emoji = Column(String(32), nullable=False)
    position = Column(Integer, default=0)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(32), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # العلاقات
    pack = relationship("StickerPack", back_populates="stickers")
    
    def __repr__(self):
        return f"<Sticker(file_id={self.file_id}, emoji={self.emoji})>"

class Settings(Base):
    """جدول الإعدادات العامة"""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Log(Base):
    """جدول السجلات"""
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=True)
    action = Column(String(32), nullable=False)
    details = Column(Text, nullable=True)
    level = Column(String(16), default="INFO")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # العلاقات
    user = relationship("User", back_populates="logs")
    
    def __repr__(self):
        return f"<Log(user_id={self.user_id}, action={self.action})>"

class UserState(Base):
    """جدول حالة المستخدم المؤقتة"""
    __tablename__ = "user_states"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    state = Column(String(32), nullable=False)
    data = Column(Text, nullable=True)  # JSON data
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
