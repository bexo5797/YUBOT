# bot/utils/validators.py
"""
مدقق الصحة للملفات والمدخلات
"""
from typing import Optional, Tuple
import os
from pathlib import Path
import mimetypes
from PIL import Image
import subprocess
from .logger import logger

class FileValidator:
    """مدقق الملفات المرفوعة"""
    
    ALLOWED_PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']
    ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm']
    
    @staticmethod
    def validate_photo(file_path: str, max_size: int = 10*1024*1024) -> Tuple[bool, str]:
        """
        التحقق من صحة ملف الصورة
        
        المعاملات:
            file_path: مسار الملف
            max_size: الحجم الأقصى بالبايت
            
        المخرجات:
            (صالح, رسالة الخطأ)
        """
        try:
            # التحقق من وجود الملف
            if not os.path.exists(file_path):
                return False, "الملف غير موجود"
            
            # التحقق من حجم الملف
            file_size = os.path.getsize(file_path)
            if file_size > max_size:
                return False, f"حجم الملف كبير جداً. الحد الأقصى: {max_size//1024//1024} ميجابايت"
            
            # التحقق من نوع الملف
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type not in FileValidator.ALLOWED_PHOTO_TYPES:
                return False, "نوع الملف غير مدعوم. الأنواع المدعومة: JPEG, PNG, WebP"
            
            # التحقق من صحة الصورة
            with Image.open(file_path) as img:
                img.verify()
            
            return True, "الملف صالح"
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من الصورة: {e}")
            return False, "الملف تالف أو غير صالح"
    
    @staticmethod
    def validate_video(
        file_path: str,
        max_size: int = 50*1024*1024,
        max_duration: int = 3
    ) -> Tuple[bool, str]:
        """
        التحقق من صحة ملف الفيديو
        
        المعاملات:
            file_path: مسار الملف
            max_size: الحجم الأقصى بالبايت
            max_duration: المدة القصوى بالثواني
            
        المخرجات:
            (صالح, رسالة الخطأ)
        """
        try:
            # التحقق من وجود الملف
            if not os.path.exists(file_path):
                return False, "الملف غير موجود"
            
            # التحقق من حجم الملف
            file_size = os.path.getsize(file_path)
            if file_size > max_size:
                return False, f"حجم الملف كبير جداً. الحد الأقصى: {max_size//1024//1024} ميجابايت"
            
            # التحقق من نوع الملف
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type not in FileValidator.ALLOWED_VIDEO_TYPES:
                return False, "نوع الفيديو غير مدعوم. الأنواع المدعومة: MP4, WebM"
            
            # التحقق من مدة الفيديو
            duration = FileValidator._get_video_duration(file_path)
            if duration is None:
                return False, "تعذر قراءة مدة الفيديو"
            
            if duration > max_duration:
                return False, f"مدة الفيديو طويلة جداً. الحد الأقصى: {max_duration} ثواني"
            
            return True, "الملف صالح"
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من الفيديو: {e}")
            return False, "الملف تالف أو غير صالح"
    
    @staticmethod
    def _get_video_duration(file_path: str) -> Optional[float]:
        """الحصول على مدة الفيديو باستخدام FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
            return None
        except Exception:
            return None

class RateLimiter:
    """محدد معدل الطلبات"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        المعاملات:
            max_requests: الحد الأقصى للطلبات
            time_window: النافذة الزمنية بالثواني
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """
        التحقق مما إذا كان المستخدم مسموحاً له بالإرسال
        """
        import time
        current_time = time.time()
        
        # تنظيف الطلبات القديمة
        if user_id in self.requests:
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if current_time - req_time < self.time_window
            ]
        
        # التحقق من عدد الطلبات
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # إضافة الطلب الحالي
        self.requests[user_id].append(current_time)
        return True

# إنشاء نسخة عالمية من محدد المعدل
rate_limiter = RateLimiter(max_requests=20, time_window=60)
