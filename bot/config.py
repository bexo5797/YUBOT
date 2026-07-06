# bot/config.py
"""
إدارة الإعدادات لبوت الملصقات
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    """إعدادات التطبيق المحملة من متغيرات البيئة"""
    
    # إعدادات البوت
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "sticker_bot")
    WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
    
    # إعدادات الخادم
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # إعدادات قاعدة البيانات
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bot.db")
    
    # حدود الملفات
    MAX_PHOTO_SIZE: int = 10 * 1024 * 1024  # 10 ميجابايت
    MAX_VIDEO_SIZE: int = 50 * 1024 * 1024  # 50 ميجابايت
    MAX_VIDEO_DURATION: int = 3  # 3 ثواني
    STICKER_SIZE: int = 512  # 512×512 بكسل
    
    # إعدادات FFmpeg
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")
    
    # دعم اللغات
    SUPPORTED_LANGUAGES: list = None
    
    def __post_init__(self):
        self.SUPPORTED_LANGUAGES = ["ar", "en"]
        
        # التأكد من وجود التوكن
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN غير موجود في متغيرات البيئة")
    
    @property
    def is_webhook(self) -> bool:
        """هل التطبيق يعمل بنظام webhook"""
        return bool(self.WEBHOOK_URL)

settings = Settings()
