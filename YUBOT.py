import os
import logging
import re
import time
import uuid
import subprocess
import asyncio
from datetime import datetime
from collections import defaultdict
from typing import Optional
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackContext,
    CallbackQueryHandler,
    ContextTypes
)
from telegram.constants import ChatAction

# ==================== الإعدادات الأساسية ====================

# قراءة التوكن من المتغيرات البيئية
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("⚠️ لم يتم تعيين BOT_TOKEN! أضفه في متغيرات البيئة.")

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== إعدادات البوت ====================

class BotConfig:
    """إعدادات البوت المركزية"""
    TEMP_FOLDER = "temp_audio"
    MAX_FILE_SIZE_MB = 50
    MAX_DURATION_MINUTES = 20
    MAX_CONCURRENT_DOWNLOADS = 3
    DOWNLOAD_TIMEOUT = 300
    CLEANUP_INTERVAL_HOURS = 1
    MAX_RETRIES = 3
    RATE_LIMIT_REQUESTS = 5
    RATE_LIMIT_PERIOD = 60
    DEFAULT_QUALITY = '128k'
    MAX_QUEUE_SIZE = 100

os.makedirs(BotConfig.TEMP_FOLDER, exist_ok=True)

# ==================== إدارة المستخدمين ====================

class UserManager:
    """إدارة المستخدمين وحماية من الإساءة"""
    def __init__(self):
        self.user_requests = defaultdict(list)
        self.user_queues = defaultdict(list)
        self.active_downloads = {}
        self.total_processed = 0
        self.blocked_users = set()
        
    def check_rate_limit(self, user_id: int) -> bool:
        if user_id in self.blocked_users:
            return False
            
        now = time.time()
        self.user_requests[user_id] = [
            t for t in self.user_requests[user_id] 
            if now - t < BotConfig.RATE_LIMIT_PERIOD
        ]
        
        if len(self.user_requests[user_id]) >= BotConfig.RATE_LIMIT_REQUESTS:
            return False
            
        self.user_requests[user_id].append(now)
        return True
    
    def add_to_queue(self, user_id: int, url: str, chat_id: int, message_id: int):
        if len(self.user_queues[user_id]) >= BotConfig.MAX_QUEUE_SIZE:
            return False
            
        self.user_queues[user_id].append({
            'url': url,
            'chat_id': chat_id,
            'message_id': message_id,
            'timestamp': time.time()
        })
        return True
    
    def get_next_in_queue(self, user_id: int):
        if self.user_queues[user_id]:
            return self.user_queues[user_id].pop(0)
        return None
    
    def is_user_busy(self, user_id: int) -> bool:
        return user_id in self.active_downloads
    
    def set_user_busy(self, user_id: int):
        self.active_downloads[user_id] = time.time()
    
    def set_user_free(self, user_id: int):
        if user_id in self.active_downloads:
            del self.active_downloads[user_id]
    
    def increment_processed(self):
        self.total_processed += 1

user_manager = UserManager()

# ==================== معالجة الفيديو ====================

class VideoProcessor:
    """معالجة فيديوهات يوتيوب"""
    def __init__(self):
        self.download_semaphore = asyncio.Semaphore(BotConfig.MAX_CONCURRENT_DOWNLOADS)
    
    async def download_audio(self, url: str, user_id: int) -> Optional[tuple]:
        async with self.download_semaphore:
            try:
                # إعدادات التحميل
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '128',
                    }],
                    'outtmpl': os.path.join(BotConfig.TEMP_FOLDER, f'{user_id}_%(title)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    'restrictfilenames': True,
                    'noplaylist': True,
                    'extractaudio': True,
                    'audioformat': 'mp3',
                    'ignoreerrors': True,
                    'nooverwrites': True,
                    'continuedl': True,
                    'retries': BotConfig.MAX_RETRIES,
                    'fragment_retries': BotConfig.MAX_RETRIES,
                    'buffersize': 1024 * 1024,
                    'http_chunk_size': 10485760,
                }
                
                # تنفيذ التحميل في thread منفصل
                loop = asyncio.get_running_loop()
                info, audio_file = await loop.run_in_executor(
                    None, 
                    self._download_sync, 
                    url, 
                    ydl_opts,
                    user_id
                )
                
                if not audio_file or not os.path.exists(audio_file):
                    return None, None
                
                # التحقق من مدة الفيديو
                duration = info.get('duration', 0) if info else 0
                if duration > BotConfig.MAX_DURATION_MINUTES * 60:
                    os.remove(audio_file)
                    raise ValueError(f"الفيديو طويل جداً ({duration//60} دقيقة)")
                
                # ضغط الملف إذا كان كبيراً
                file_size = os.path.getsize(audio_file) / (1024 * 1024)
                if file_size > BotConfig.MAX_FILE_SIZE_MB:
                    compressed_file = await self.compress_audio(audio_file, user_id)
                    if compressed_file:
                        os.remove(audio_file)
                        audio_file = compressed_file
                
                return audio_file, info.get('title', 'الصوت') if info else ('الصوت', None)
                
            except Exception as e:
                logger.error(f"خطأ في تحميل {url}: {e}")
                return None, None
    
    def _download_sync(self, url: str, ydl_opts: dict, user_id: int):
        """دالة التحميل المتزامنة"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    return None, None
                
                # البحث عن الملف المحمل
                base_filename = ydl.prepare_filename(info)
                audio_file = None
                
                for ext in ['.mp3', '.m4a', '.webm', '.opus']:
                    test_file = base_filename.rsplit('.', 1)[0] + ext
                    if os.path.exists(test_file):
                        audio_file = test_file
                        break
                
                if not audio_file:
                    # البحث في مجلد المستخدم
                    user_pattern = f"{user_id}_"
                    for file in os.listdir(BotConfig.TEMP_FOLDER):
                        if file.startswith(user_pattern) and file.endswith(('.mp3', '.m4a', '.webm')):
                            audio_file = os.path.join(BotConfig.TEMP_FOLDER, file)
                            break
                
                return info, audio_file
                
        except Exception as e:
            logger.error(f"خطأ في التحميل المتزامن: {e}")
            return None, None
    
    async def compress_audio(self, input_path: str, user_id: int) -> Optional[str]:
        """ضغط الصوت باستخدام FFmpeg"""
        try:
            output_path = os.path.join(
                BotConfig.TEMP_FOLDER, 
                f"{user_id}_compressed_{uuid.uuid4()}.mp3"
            )
            
            cmd = [
                'ffmpeg', '-i', input_path,
                '-ac', '1',
                '-ar', '22050',
                '-b:a', '64k',
                '-y',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            
            if process.returncode == 0 and os.path.exists(output_path):
                return output_path
            return None
            
        except Exception as e:
            logger.error(f"خطأ في الضغط: {e}")
            return None

video_processor = VideoProcessor()

# ==================== معالجات البوت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    user = update.effective_user
    welcome_msg = (
        f"🎵 *مرحباً {user.first_name}!*\n\n"
        "أنا بوت تحميل الصوتيات من يوتيوب 🎧\n\n"
        "📌 *كيفية الاستخدام:*\n"
        "• أرسل رابط فيديو يوتيوب\n"
        "• سأقوم بتحويله إلى صوت MP3\n\n"
        f"⚡ الحد الأقصى: {BotConfig.MAX_DURATION_MINUTES} دقيقة\n"
        f"📊 تم معالجة {user_manager.total_processed} طلب"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("❓ مساعدة", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة المساعدة"""
    help_msg = (
        "❓ *تعليمات الاستخدام*\n\n"
        "1️⃣ أرسل رابط يوتيوب\n"
        "2️⃣ انتظر التحميل والتحويل\n"
        "3️⃣ استلم الصوت مباشرة\n\n"
        f"📌 الحد الأقصى: {BotConfig.MAX_DURATION_MINUTES} دقيقة"
    )
    await update.message.reply_text(help_msg, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات البوت"""
    stats_msg = (
        "📊 *إحصائيات البوت*\n\n"
        f"📈 المعالجات: {user_manager.total_processed}\n"
        f"👥 المستخدمون النشطون: {len(user_manager.active_downloads)}\n"
        f"📋 في الانتظار: {sum(len(q) for q in user_manager.user_queues.values())}"
    )
    await update.message.reply_text(stats_msg, parse_mode='Markdown')

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء الطلبات"""
    user_id = update.effective_user.id
    
    if user_id in user_manager.active_downloads:
        user_manager.set_user_free(user_id)
    
    if user_id in user_manager.user_queues and user_manager.user_queues[user_id]:
        count = len(user_manager.user_queues[user_id])
        user_manager.user_queues[user_id] = []
        await update.message.reply_text(f"✅ تم إلغاء {count} طلب")
    else:
        await update.message.reply_text("📭 ليس لديك طلبات معلقة")

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الانتظار"""
    user_id = update.effective_user.id
    queue = user_manager.user_queues.get(user_id, [])
    
    if not queue:
        await update.message.reply_text("📭 قائمة الانتظار فارغة")
        return
    
    queue_msg = "📋 *قائمة الانتظار:*\n\n"
    for i, item in enumerate(queue[:10], 1):
        queue_msg += f"{i}. {item['url'][:40]}...\n"
    
    await update.message.reply_text(queue_msg, parse_mode='Markdown')

async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة روابط يوتيوب"""
    user_id = update.effective_user.id
    message = update.message
    text = message.text
    
    # التحقق من الحد الأدنى للطلبات
    if not user_manager.check_rate_limit(user_id):
        await message.reply_text(
            "⏳ *تم تجاوز حد الطلبات!*\n"
            f"الحد: {BotConfig.RATE_LIMIT_REQUESTS} طلب في الدقيقة",
            parse_mode='Markdown'
        )
        return
    
    # البحث عن روابط يوتيوب
    youtube_pattern = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|m\.youtube\.com)/\S+)'
    urls = re.findall(youtube_pattern, text)
    
    if not urls:
        await message.reply_text("❌ لم أجد رابط يوتيوب صحيح!")
        return
    
    # التحقق من حالة المستخدم
    if user_manager.is_user_busy(user_id):
        await message.reply_text("⏳ لديك طلب قيد المعالجة! سيتم وضع روابطك في قائمة الانتظار.")
        for url in urls:
            user_manager.add_to_queue(user_id, url, message.chat_id, message.message_id)
        return
    
    # معالجة الروابط
    user_manager.set_user_busy(user_id)
    
    try:
        processing_msg = await message.reply_text(f"⏳ جاري تحميل {len(urls)} صوت...")
        
        success_count = 0
        fail_count = 0
        
        for idx, url in enumerate(urls, 1):
            try:
                await context.bot.send_chat_action(
                    chat_id=message.chat_id,
                    action=ChatAction.UPLOAD_AUDIO
                )
                
                # تحميل الصوت
                audio_path, title = await video_processor.download_audio(url, user_id)
                
                if not audio_path or not os.path.exists(audio_path):
                    fail_count += 1
                    await message.reply_text(f"❌ فشل تحميل الرابط {idx}")
                    continue
                
                # إرسال الصوت
                with open(audio_path, 'rb') as audio_file:
                    await message.reply_audio(
                        audio=audio_file,
                        title=title[:60] if title else "صوت",
                        performer="YouTube",
                        caption=f"🎵 *{title}*\n\n✅ تم التحويل بنجاح!",
                        parse_mode='Markdown'
                    )
                
                # حذف الملف
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                
                success_count += 1
                user_manager.increment_processed()
                
            except Exception as e:
                logger.error(f"خطأ في معالجة الرابط {url}: {e}")
                fail_count += 1
        
        # تحديث رسالة المعالجة
        summary = f"✅ *اكتملت المعالجة!*\n\n✓ نجح: {success_count}\n✗ فشل: {fail_count}"
        await processing_msg.edit_text(summary, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"خطأ عام: {e}")
        await message.reply_text("⚠️ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
    
    finally:
        user_manager.set_user_free(user_id)
        
        # معالجة قائمة الانتظار
        await process_user_queue(user_id)

async def process_user_queue(user_id: int):
    """معالجة قائمة انتظار المستخدم"""
    while True:
        next_request = user_manager.get_next_in_queue(user_id)
        if not next_request:
            break
        
        # إنشاء طلب جديد من قائمة الانتظار
        class FakeMessage:
            def __init__(self, chat_id, text):
                self.chat_id = chat_id
                self.text = text
                self.message_id = None
                self.from_user = type('User', (), {'id': user_id})()
        
        class FakeUpdate:
            def __init__(self, chat_id, text):
                self.message = FakeMessage(chat_id, text)
                self.effective_user = type('User', (), {'id': user_id})()
                self.effective_chat = type('Chat', (), {'id': chat_id})()
        
        fake_update = FakeUpdate(
            next_request['chat_id'],
            next_request['url']
        )
        await handle_youtube_link(fake_update, None)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار الاتصال"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        stats_msg = (
            "📊 *إحصائيات البوت*\n\n"
            f"📈 المعالجات: {user_manager.total_processed}\n"
            f"👥 النشطون: {len(user_manager.active_downloads)}\n"
            f"📋 في الانتظار: {sum(len(q) for q in user_manager.user_queues.values())}"
        )
        await query.edit_message_text(stats_msg, parse_mode='Markdown')
    
    elif query.data == "help":
        help_msg = (
            "❓ *كيفية الاستخدام*\n\n"
            "1. أرسل رابط يوتيوب\n"
            "2. انتظر التحميل والتحويل\n"
            "3. استلم الصوت مباشرة"
        )
        await query.edit_message_text(help_msg, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأخطاء"""
    logger.error(f"خطأ: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ حدث خطأ. يرجى المحاولة مرة أخرى.")

def cleanup_temp_files():
    """تنظيف الملفات المؤقتة"""
    try:
        now = time.time()
        for file in os.listdir(BotConfig.TEMP_FOLDER):
            file_path = os.path.join(BotConfig.TEMP_FOLDER, file)
            if os.path.isfile(file_path):
                if now - os.path.getctime(file_path) > BotConfig.CLEANUP_INTERVAL_HOURS * 3600:
                    os.remove(file_path)
                    logger.info(f"تم حذف: {file}")
    except Exception as e:
        logger.error(f"خطأ في التنظيف: {e}")

# ==================== التشغيل الرئيسي ====================

def main():
    """تشغيل البوت"""
    try:
        # إنشاء التطبيق
        application = Application.builder().token(BOT_TOKEN).build()
        
        # إضافة المعالجات
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(CommandHandler("queue", queue_command))
        
        # معالجة الروابط
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            handle_youtube_link
        ))
        
        # معالجة الملفات الصوتية
        application.add_handler(MessageHandler(
            filters.AUDIO | filters.VOICE, 
            lambda u, c: u.message.reply_text("🎵 أرسل رابط يوتيوب فقط!")
        ))
        
        # معالجة الأزرار
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # معالجة الأخطاء
        application.add_error_handler(error_handler)
        
        # تشغيل البوت
        logger.info("🤖 البوت يعمل...")
        print(f"🤖 البوت يعمل مع التوكن: {BOT_TOKEN[:10]}...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"خطأ فادح: {e}")
        raise

if __name__ == "__main__":
    main()
