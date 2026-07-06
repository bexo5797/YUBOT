# bot/services/video_service.py
"""
خدمة معالجة الفيديو وتحويله لملصقات متحركة
"""
import subprocess
import os
from pathlib import Path
from typing import Tuple, Optional
import asyncio
from ..utils.logger import logger

class VideoService:
    """خدمة معالجة الفيديو"""
    
    MAX_SIZE = 512  # الحد الأقصى لحجم الملصق
    MAX_DURATION = 3  # المدة القصوى بالثواني
    MAX_FPS = 30  # الحد الأقصى للإطارات في الثانية
    
    @staticmethod
    async def process_video(
        input_path: str,
        output_path: str,
        resize: bool = True,
        optimize: bool = True
    ) -> Tuple[bool, str]:
        """
        معالجة الفيديو وتحويله لملصق متحرك
        
        المعاملات:
            input_path: مسار الفيديو المدخل
            output_path: مسار حفظ الملصق
            resize: تغيير الحجم
            optimize: تحسين الجودة
            
        المخرجات:
            (نجاح, رسالة)
        """
        try:
            # التحقق من مدة الفيديو
            duration = await VideoService._get_duration(input_path)
            if duration > VideoService.MAX_DURATION:
                # قص الفيديو
                temp_path = input_path + "_trimmed.mp4"
                success, msg = await VideoService._trim_video(
                    input_path,
                    temp_path,
                    0,
                    VideoService.MAX_DURATION
                )
                if not success:
                    return False, msg
                input_path = temp_path
            
            # بناء أمر FFmpeg
            cmd = await VideoService._build_ffmpeg_command(
                input_path,
                output_path,
                resize,
                optimize
            )
            
            # تنفيذ الأمر
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "خطأ غير معروف"
                logger.error(f"خطأ FFmpeg: {error_msg}")
                return False, f"فشل في معالجة الفيديو: {error_msg[:100]}"
            
            # التحقق من حجم الملف الناتج
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                if file_size > 256 * 1024:  # 256KB حد أقصى للملصقات المتحركة
                    # محاولة تحسين إضافي
                    await VideoService._optimize_webm(output_path)
            
            # تنظيف الملفات المؤقتة
            if input_path.endswith("_trimmed.mp4"):
                os.remove(input_path)
            
            return True, "تمت معالجة الفيديو بنجاح"
            
        except Exception as e:
            logger.error(f"خطأ في معالجة الفيديو: {e}")
            return False, str(e)
    
    @staticmethod
    async def _build_ffmpeg_command(
        input_path: str,
        output_path: str,
        resize: bool,
        optimize: bool
    ) -> list:
        """بناء أمر FFmpeg"""
        cmd = ['ffmpeg', '-y', '-i', input_path]
        
        # إعدادات التصفية
        filter_parts = []
        
        if resize:
            filter_parts.append(
                f"scale={VideoService.MAX_SIZE}:{VideoService.MAX_SIZE}:force_original_aspect_ratio=decrease"
            )
            filter_parts.append(f"pad={VideoService.MAX_SIZE}:{VideoService.MAX_SIZE}:-1:-1:color=0x00000000")
        
        # إعدادات الإطارات
        filter_parts.append(f"fps={VideoService.MAX_FPS}")
        
        if filter_parts:
            cmd.extend(['-vf', ','.join(filter_parts)])
        
        # إعدادات التشفير
        if optimize:
            cmd.extend([
                '-c:v', 'libvpx-vp9',
                '-crf', '30',
                '-b:v', '0',
                '-deadline', 'realtime',
                '-cpu-used', '5'
            ])
        else:
            cmd.extend([
                '-c:v', 'libvpx-vp9',
                '-crf', '20',
                '-b:v', '0'
            ])
        
        # إعدادات الصوت (إزالة)
        cmd.extend(['-an'])
        
        # المخرجات
        cmd.extend([
            '-f', 'webm',
            '-loop', '0',
            '-pix_fmt', 'yuva420p',
            output_path
        ])
        
        return cmd
    
    @staticmethod
    async def _get_duration(input_path: str) -> float:
        """الحصول على مدة الفيديو"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            return float(stdout.decode().strip())
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على مدة الفيديو: {e}")
            return 0.0
    
    @staticmethod
    async def _trim_video(
        input_path: str,
        output_path: str,
        start: float,
        duration: float
    ) -> Tuple[bool, str]:
        """قص الفيديو"""
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-ss', str(start),
                '-t', str(duration),
                '-c', 'copy',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                return True, "تم قص الفيديو بنجاح"
            return False, "فشل في قص الفيديو"
            
        except Exception as e:
            logger.error(f"خطأ في قص الفيديو: {e}")
            return False, str(e)
    
    @staticmethod
    async def _optimize_webm(file_path: str):
        """تحسين ملف WebM"""
        try:
            temp_path = file_path + "_optimized.webm"
            cmd = [
                'ffmpeg', '-y',
                '-i', file_path,
                '-c:v', 'libvpx-vp9',
                '-crf', '35',
                '-b:v', '0',
                '-deadline', 'realtime',
                '-cpu-used', '8',
                '-an',
                temp_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                os.replace(temp_path, file_path)
            
        except Exception as e:
            logger.error(f"خطأ في تحسين WebM: {e}")
    
    @staticmethod
    async def extract_thumbnail(
        input_path: str,
        output_path: str,
        time_pos: float = 0.5
    ) -> Tuple[bool, str]:
        """استخراج صورة مصغرة من الفيديو"""
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-ss', str(time_pos),
                '-vframes', '1',
                '-q:v', '2',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if os.path.exists(output_path):
                return True, "تم استخراج الصورة المصغرة"
            return False, "فشل في استخراج الصورة"
            
        except Exception as e:
            logger.error(f"خطأ في استخراج الصورة المصغرة: {e}")
            return False, str(e)
