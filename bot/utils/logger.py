# bot/utils/logger.py
"""
نظام التسجيل الاحترافي للتطبيق
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

# إنشاء مجلد السجلات
log_dir = Path("data/logs")
log_dir.mkdir(parents=True, exist_ok=True)

def setup_logger(
    name: str = "sticker_bot",
    log_file: Optional[str] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    إعداد مسجل احترافي مع دعم الملفات والكونسول
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # منع تكرار المعالجات
    if logger.handlers:
        return logger
    
    # تنسيق الرسائل
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # معالج الكونسول
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    
    # معالج الملفات
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10 ميجابايت
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
    
    # معالج ملفات الأخطاء
    error_handler = RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)
    
    return logger

# إنشاء المسجل الرئيسي
logger = setup_logger(log_file=log_dir / "bot.log")
