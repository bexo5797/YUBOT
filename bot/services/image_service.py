# bot/services/image_service.py
"""
خدمة معالجة الصور وتحويلها لملصقات
"""
from PIL import Image, ImageDraw, ImageFilter
import io
from pathlib import Path
from typing import Tuple, Optional
import os
from ..utils.logger import logger

class ImageService:
    """خدمة معالجة الصور"""
    
    MAX_SIZE = 512  # الحد الأقصى لحجم الملصق
    WEBP_QUALITY = 95  # جودة WebP
    
    @staticmethod
    async def process_image(
        input_path: str,
        output_path: str,
        background: str = "transparent"
    ) -> Tuple[bool, str]:
        """
        معالجة الصورة وتحويلها لملصق
        
        المعاملات:
            input_path: مسار الصورة المدخلة
            output_path: مسار حفظ الملصق
            background: نوع الخلفية (transparent, white, auto)
            
        المخرجات:
            (نجاح, رسالة)
        """
        try:
            # فتح الصورة
            with Image.open(input_path) as img:
                # تحويل لـ RGBA إذا كانت الخلفية شفافة
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # تغيير حجم الصورة مع الحفاظ على النسبة
                resized_img = ImageService._resize_image(img, ImageService.MAX_SIZE)
                
                # معالجة الخلفية
                if background == "transparent":
                    processed_img = ImageService._handle_transparency(resized_img)
                elif background == "white":
                    processed_img = ImageService._add_white_background(resized_img)
                else:
                    processed_img = ImageService._auto_background(resized_img)
                
                # حفظ كملف WebP
                processed_img.save(
                    output_path,
                    'WEBP',
                    quality=ImageService.WEBP_QUALITY,
                    method=6  # أفضل ضغط
                )
                
                # التحقق من حجم الملف الناتج
                file_size = os.path.getsize(output_path)
                if file_size > 512 * 1024:  # 512KB حد أقصى لملصق تيليجرام
                    # تقليل الجودة إذا كان الحجم كبيراً
                    for quality in range(90, 60, -10):
                        processed_img.save(
                            output_path,
                            'WEBP',
                            quality=quality,
                            method=6
                        )
                        if os.path.getsize(output_path) <= 512 * 1024:
                            break
                
                return True, "تمت معالجة الصورة بنجاح"
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الصورة: {e}")
            return False, f"فشل في معالجة الصورة: {str(e)}"
    
    @staticmethod
    def _resize_image(img: Image.Image, max_size: int) -> Image.Image:
        """تغيير حجم الصورة مع الحفاظ على النسبة"""
        width, height = img.size
        
        # إذا كان كلا البعدين أقل من الحد الأقصى
        if width <= max_size and height <= max_size:
            # تكبير الصورة للحصول على جودة أفضل
            ratio = max_size / max(width, height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # حساب النسبة الجديدة
        ratio = max_size / max(width, height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    @staticmethod
    def _handle_transparency(img: Image.Image) -> Image.Image:
        """معالجة الخلفية الشفافة"""
        # إنشاء صورة جديدة بخلفية شفافة
        background = Image.new('RGBA', (ImageService.MAX_SIZE, ImageService.MAX_SIZE), (0, 0, 0, 0))
        
        # توسيط الصورة
        x_offset = (ImageService.MAX_SIZE - img.width) // 2
        y_offset = (ImageService.MAX_SIZE - img.height) // 2
        
        # لصق الصورة
        background.paste(img, (x_offset, y_offset), img)
        
        return background
    
    @staticmethod
    def _add_white_background(img: Image.Image) -> Image.Image:
        """إضافة خلفية بيضاء"""
        background = Image.new('RGBA', (ImageService.MAX_SIZE, ImageService.MAX_SIZE), (255, 255, 255, 255))
        
        x_offset = (ImageService.MAX_SIZE - img.width) // 2
        y_offset = (ImageService.MAX_SIZE - img.height) // 2
        
        background.paste(img, (x_offset, y_offset), img)
        
        return background
    
    @staticmethod
    def _auto_background(img: Image.Image) -> Image.Image:
        """تحديد الخلفية تلقائياً"""
        # حساب نسبة الشفافية
        alpha = img.split()[3]
        transparent_pixels = sum(1 for pixel in alpha.getdata() if pixel < 128)
        total_pixels = alpha.size[0] * alpha.size[1]
        transparency_ratio = transparent_pixels / total_pixels
        
        if transparency_ratio > 0.3:
            # استخدام خلفية شفافة
            return ImageService._handle_transparency(img)
        else:
            # استخدام خلفية بيضاء
            return ImageService._add_white_background(img)
    
    @staticmethod
    async def add_watermark(
        input_path: str,
        output_path: str,
        text: str = "",
        position: str = "bottom-right"
    ) -> Tuple[bool, str]:
        """إضافة علامة مائية للصورة"""
        try:
            with Image.open(input_path) as img:
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # إنشاء طبقة العلامة المائية
                txt = Image.new('RGBA', img.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(txt)
                
                # إعدادات النص
                from PIL import ImageFont
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    font = ImageFont.load_default()
                
                # تحديد موقع النص
                if position == "bottom-right":
                    text_position = (img.width - 150, img.height - 40)
                elif position == "bottom-left":
                    text_position = (10, img.height - 40)
                elif position == "top-right":
                    text_position = (img.width - 150, 10)
                else:
                    text_position = (10, 10)
                
                # رسم النص
                draw.text(text_position, text, font=font, fill=(255, 255, 255, 128))
                
                # دمج الطبقات
                watermarked = Image.alpha_composite(img, txt)
                watermarked.save(output_path, 'WEBP', quality=95)
                
                return True, "تمت إضافة العلامة المائية"
                
        except Exception as e:
            logger.error(f"خطأ في إضافة العلامة المائية: {e}")
            return False, str(e)

    @staticmethod
    async def create_preview(
        input_path: str,
        output_path: str,
        size: int = 256
    ) -> Tuple[bool, str]:
        """إنشاء معاينة للصورة"""
        try:
            with Image.open(input_path) as img:
                # تصغير الصورة
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                
                # حفظ المعاينة
                img.save(output_path, 'PNG')
                
                return True, "تم إنشاء المعاينة"
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء المعاينة: {e}")
            return False, str(e)
