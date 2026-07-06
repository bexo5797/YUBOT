# bot/utils/helpers.py
"""
أدوات مساعدة للبوت
"""
import re
import emoji
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import hashlib
import random
import string

def generate_unique_id() -> str:
    """توليد معرف فريد"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{timestamp}_{random_str}"

def sanitize_pack_name(name: str) -> str:
    """تنظيف اسم الحزمة"""
    # إزالة المسافات الزائدة
    name = ' '.join(name.split())
    # إزالة الأحرف غير المسموح بها
    name = re.sub(r'[^\w\s\u0600-\u06FF]', '', name)
    # تحديد الطول
    return name[:64].strip()

def validate_emoji(text: str) -> Tuple[bool, str]:
    """التحقق من صحة الإيموجي"""
    if not text:
        return False, "الإيموجي مطلوب"
    
    # استخراج الإيموجي فقط
    emojis = [c for c in text if c in emoji.EMOJI_DATA]
    
    if not emojis:
        return False, "الرجاء إرسال إيموجي صالح"
    
    if len(emojis) > 1:
        return False, "الرجاء إرسال إيموجي واحد فقط"
    
    return True, emojis[0]

def validate_sticker_name(name: str) -> Tuple[bool, str]:
    """التحقق من صحة اسم الملصق"""
    pattern = r'^[a-zA-Z0-9_]+$'
    
    if not name or len(name) < 2:
        return False, "اسم الملصق يجب أن يكون حرفين على الأقل"
    
    if not re.match(pattern, name):
        return False, "اسم الملصق يجب أن يحتوي على أحرف إنجليزية وأرقام و _ فقط"
    
    if len(name) > 64:
        return False, "اسم الملصق طويل جداً (الحد الأقصى 64 حرف)"
    
    return True, name

def format_size(size_bytes: int) -> str:
    """تنسيق حجم الملف"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def format_duration(seconds: float) -> str:
    """تنسيق المدة الزمنية"""
    return f"{seconds:.1f} ثانية"

def generate_pack_share_link(pack_name: str) -> str:
    """توليد رابط مشاركة الحزمة"""
    return f"https://t.me/addstickers/{pack_name}"

def get_timestamp() -> str:
    """الحصول على الطابع الزمني الحالي"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def truncate_text(text: str, max_length: int = 100) -> str:
    """قص النص مع إضافة ..."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

class Cache:
    """نظام تخزين مؤقت بسيط"""
    
    def __init__(self, ttl_seconds: int = 300):
        self._cache = {}
        self._ttl = ttl_seconds
    
    def set(self, key: str, value: any):
        """حفظ قيمة في الذاكرة المؤقتة"""
        self._cache[key] = {
            'value': value,
            'expires': datetime.now() + timedelta(seconds=self._ttl)
        }
    
    def get(self, key: str) -> Optional[any]:
        """استرجاع قيمة من الذاكرة المؤقتة"""
        if key in self._cache:
            item = self._cache[key]
            if datetime.now() < item['expires']:
                return item['value']
            del self._cache[key]
        return None
    
    def delete(self, key: str):
        """حذف قيمة من الذاكرة المؤقتة"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self):
        """مسح الذاكرة المؤقتة"""
        self._cache.clear()
