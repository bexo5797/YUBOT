# bot/config.py
"""
Configuration management for the Telegram Sticker Bot.
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    
    # Bot Configuration
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "sticker_bot")
    WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
    
    # Server Configuration
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bot.db")
    
    # File Limits
    MAX_PHOTO_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_VIDEO_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_VIDEO_DURATION: int = 3  # 3 seconds
    STICKER_SIZE: int = 512  # 512x
