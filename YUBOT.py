import os
import logging
import re
import time
import uuid
import subprocess
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, Dict, List
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
import psutil
import json

# ==================== الإعدادات الأساسية ====================

# قراءة التوكن من المتغيرات البيئية
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("⚠️ لم يتم تعيين BOT_TOKEN! أضفه في متغيرات البيئة.")

# إعدادات التسجيل المتقدمة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== إعدادات البوت ====================

class BotConfig:
    """إعدادات البوت المركزية"""
    TEMP_FOLDER = "temp_audio"
    MAX_FILE_SIZE_MB = 50  # الحد الأقصى لحجم الملف قبل الضغط
    MAX_DURATION_MINUTES = 20  # الحد الأقصى لطول الفيديو
    MAX_CONCURRENT_DOWNLOADS = 3  # عدد التحميلات المتزامنة
    DOWNLOAD_TIMEOUT = 300  # 5 دقائق مهلة التحميل
    CLEANUP_INTERVAL_HOURS = 1  # تنظيف الملفات كل ساعة
    MAX_RETRIES = 3  # عدد محاولات إعادة التحميل
    RATE_LIMIT_REQUESTS = 5  # عدد الطلبات المسموحة في الدقيقة
    RATE_LIMIT_PERIOD = 60  # الفترة بالثواني
    
    # الإعدادات المتقدمة
    ALLOWED_QUALITIES = ['64k', '128k', '192k', '320k']
    DEFAULT_QUALITY = '128k'
    MAX_QUEUE_SIZE = 100  # الحد الأقصى لقائمة الانتظار

os.makedirs(BotConfig.TEMP_FOLDER, exist_ok=True)

# ==================== إدارة المستخدمين ====================

class UserManager:
    """إدارة المستخدمين وحماية من الإساءة"""
    def __init__(self):
        self.user_requests = defaultdict(list)  # تتبع طلبات المستخدمين
        self.user_queues = defaultdict(list)  # قوائم انتظار المستخدمين
        self.active_downloads = {}  # التحميلات النشطة
        self.total_processed = 0  # إجمالي المعالجات
        self.blocked_users = set()  # المستخدمون المحظورون
        
    def check_rate_limit(self, user_id: int) -> bool:
        """التحقق من حد الطلبات للمستخدم"""
        if user_id in self.blocked_users:
            return False
            
        now = time.time()
        # تنظيف الطلبات القديمة
        self.user_requests[user_id] = [
            t for t in self.user_requests[user_id] 
            if now - t < BotConfig.RATE_LIMIT_PERIOD
        ]
        
        if len(self.user_requests[user_id]) >= BotConfig.RATE_LIMIT_REQUESTS:
            return False
            
        self.user_requests[user_id].append(now)
        return True
    
    def add_to_queue(self, user_id: int, url: str, chat_id: int, message_id: int):
        """إضافة طلب إلى قائمة الانتظار"""
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
        """الحصول على الطلب التالي من قائمة الانتظار"""
        if self.user_queues[user_id]:
            return self.user_queues[user_id].pop(0)
        return None
    
    def is_user_busy(self, user_id: int) -> bool:
        """التحقق من أن المستخدم ليس مشغولاً"""
        return user_id in self.active_downloads
    
    def set_user_busy(self, user_id: int):
        """تعيين المستخدم كـ مشغول"""
        self.active_downloads[user_id] = time.time()
    
    def set_user_free(self, user_id: int):
        """تعيين المستخدم كـ حر"""
        if user_id in self.active_downloads:
            del self.active_downloads[user_id]
    
    def add_blocked_user(self, user_id: int, reason: str = ""):
        """حظر مستخدم"""
        self.blocked_users.add(user_id)
        logger.warning(f"تم حظر المستخدم {user_id} بسبب: {reason}")
    
    def remove_blocked_user(self, user_id: int):
        """إلغاء حظر مستخدم"""
        self.blocked_users.discard(user_id)
    
    def increment_processed(self):
        """زيادة عداد المعالجات"""
        self.total_processed += 1

user_manager = UserManager()

# ==================== معالجة الفيديو ====================

class VideoProcessor:
    """معالجة فيديوهات يوتيوب"""
    def __init__(self):
        self.download_semaphore = asyncio.Semaphore(BotConfig.MAX_CONCURRENT_DOWNLOADS)
    
    async def download_audio(self, url: str, user_id: int, quality: str = BotConfig.DEFAULT_QUALITY) -> Optional[tuple]:
        """تحميل الصوت من يوتيوب مع إدارة متزامنة"""
        async with self.download_semaphore:
            try:
                # إعدادات التحميل المتقدمة
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': quality.replace('k', ''),
                    }],
                    'outtmpl': os.path.join(BotConfig.TEMP_FOLDER, f'{user_id}_%(title)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    'restrictfilenames': True,
                    'noplaylist': True,  # عدم معالجة قوائم التشغيل
                    'extractaudio': True,
                    'audioformat': 'mp3',
                    'ignoreerrors': True,
                    'nooverwrites': True,
                    'continuedl': True,  # استئناف التحميل
                    'retries': BotConfig.MAX_RETRIES,
                    'fragment_retries': BotConfig.MAX_RETRIES,
                    'buffersize': 1024 * 1024,  # 1MB
                    'http_chunk_size': 10485760,  # 10MB
                    'throttledratelimit': 100000000,  # 100Mbps
                }
                
                # تشغيل التحميل في thread منفصل
                loop = asyncio.get_event_loop()
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
                duration = info.get('duration', 0)
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
                
                return audio_file, info.get('title', 'الصوت')
                
            except Exception as e:
                logger.error(f"خطأ في تحميل {url}: {e}")
                return None, None
    
    def _download_sync(self, url: str, ydl_opts: dict, user_id: int):
        """دالة التحميل المتزامنة"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
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
                '-ac', '1',  # Mono
                '-ar', '22050',  # 22.05 kHz
                '-b:a', '64k',  # 64 kbps
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

# ==================== دالة الحصول على اسم ملف فريد ====================

def get_unique_filename(user_id: int, title: str) -> str:
    """إنشاء اسم ملف فريد"""
    safe_title = re.sub(r'[^\w\-_\. ]', '_', title)[:50]
    return f"{user_id}_{safe_title}_{uuid.uuid4().hex[:8]}.mp3"

# ==================== معالجات البوت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    user = update.effective_user
    welcome_msg = (
        f"🎵 *مرحباً {user.first_name}!*\n\n"
        "أنا بوت تحميل الصوتيات من يوتيوب 🎧\n\n"
        "📌 *كيفية الاستخدام:*\n"
        "• أرسل رابط فيديو يوتيوب\n"
        "• سأقوم بتحويله إلى صوت MP3\n"
        "• يمكنك إرسال روابط متعددة\n\n"
        "⚡ *المميزات:*\n"
        f"• سرعة عالية مع إدارة ذكية للتحميلات\n"
        f"• ضغط تلقائي للملفات الكبيرة\n"
        f"• حد أقصى {BotConfig.MAX_DURATION_MINUTES} دقيقة\n"
        f"• دعم قوائم الانتظار\n\n"
        "🛡️ *الأمان:*\n"
        "• حماية ضد الإساءة\n"
        "• حد 5 طلبات في الدقيقة\n\n"
        "📊 *الإحصائيات:*\n"
        f"• تم معالجة {user_manager.total_processed} طلب حتى الآن\n\n"
        "🤖 *الأوامر المتاحة:*\n"
        "/start - عرض هذه الرسالة\n"
        "/help - مساعدة\n"
        "/stats - إحصائيات البوت\n"
        "/cancel - إلغاء الطلبات المعلقة\n"
        "/queue - عرض قائمة الانتظار الخاصة بك"
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
        "1️⃣ *إرسال رابط:*\n"
        "   أرسل رابط يوتيوب وسأقوم بتحميل الصوت\n\n"
        "2️⃣ *روابط متعددة:*\n"
        "   يمكنك إرسال عدة روابط في رسالة واحدة\n\n"
        "3️⃣ *قائمة الانتظار:*\n"
        "   إذا كان البوت مشغولاً، سيتم وضع طلبك في قائمة الانتظار\n\n"
        "4️⃣ *إلغاء الطلب:*\n"
        "   استخدم /cancel لإلغاء جميع طلباتك المعلقة\n\n"
        "5️⃣ *الحدود:*\n"
        f"   • {BotConfig.MAX_DURATION_MINUTES} دقيقة كحد أقصى للفيديو\n"
        f"   • {BotConfig.MAX_FILE_SIZE_MB} ميجا كحد أقصى للملف\n"
        f"   • 5 طلبات في الدقيقة كحد أقصى\n\n"
        "6️⃣ *جودة الصوت:*\n"
        "   الجودة الافتراضية 128kbps مع ضغط تلقائي عند الحاجة"
    )
    await update.message.reply_text(help_msg, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات البوت"""
    stats_msg = (
        "📊 *إحصائيات البوت*\n\n"
        f"📈 *إجمالي المعالجات:* {user_manager.total_processed}\n"
        f"👥 *المستخدمون النشطون:* {len(user_manager.active_downloads)}\n"
        f"📋 *الطلبات في الانتظار:* {sum(len(q) for q in user_manager.user_queues.values())}\n"
        f"⏱️ *وقت التشغيل:* {get_uptime()}\n"
        f"💾 *حجم الملفات المؤقتة:* {get_temp_size()}\n"
        f"🚫 *المستخدمون المحظورون:* {len(user_manager.blocked_users)}"
    )
    await update.message.reply_text(stats_msg, parse_mode='Markdown')

def get_uptime() -> str:
    """الحصول على وقت تشغيل البوت"""
    try:
        import psutil
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        return f"{hours} ساعة {minutes} دقيقة"
    except:
        return "غير معروف"

def get_temp_size() -> str:
    """الحصول على حجم الملفات المؤقتة"""
    try:
        total = 0
        for file in os.listdir(BotConfig.TEMP_FOLDER):
            file_path = os.path.join(BotConfig.TEMP_FOLDER, file)
            if os.path.isfile(file_path):
                total += os.path.getsize(file_path)
        return f"{total / (1024 * 1024):.2f} ميجا"
    except:
        return "غير معروف"

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء جميع طلبات المستخدم"""
    user_id = update.effective_user.id
    
    if user_id in user_manager.active_downloads:
        # محاولة إلغاء التحميل النشط
        user_manager.set_user_free(user_id)
    
    if user_id in user_manager.user_queues and user_manager.user_queues[user_id]:
        count = len(user_manager.user_queues[user_id])
        user_manager.user_queues[user_id] = []
        await update.message.reply_text(f"✅ تم إلغاء {count} طلب من قائمة الانتظار")
    else:
        await update.message.reply_text("📭 ليس لديك طلبات معلقة")

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الانتظار الخاصة بالمستخدم"""
    user_id = update.effective_user.id
    queue = user_manager.user_queues.get(user_id, [])
    
    if not queue:
        await update.message.reply_text("📭 قائمة الانتظار الخاصة بك فارغة")
        return
    
    queue_msg = "📋 *قائمة الانتظار الخاصة بك:*\n\n"
    for i, item in enumerate(queue[:10], 1):
        queue_msg += f"{i}. {item['url'][:40]}...\n"
    
    if len(queue) > 10:
        queue_msg += f"\n... و {len(queue) - 10} طلب آخر"
    
    await update.message.reply_text(queue_msg, parse_mode='Markdown')

async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة روابط يوتيوب مع إدارة متقدمة"""
    user_id = update.effective_user.id
    message = update.message
    text = message.text
    
    # التحقق من الحد الأدنى للطلبات
    if not user_manager.check_rate_limit(user_id):
        await message.reply_text(
            "⏳ *تم تجاوز حد الطلبات!*\n"
            f"الحد المسموح: {BotConfig.RATE_LIMIT_REQUESTS} طلب في الدقيقة\n"
            "الرجاء الانتظار قبل المحاولة مرة أخرى.",
            parse_mode='Markdown'
        )
        return
    
    # البحث عن روابط يوتيوب
    youtube_pattern = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|m\.youtube\.com)/\S+)'
    urls = re.findall(youtube_pattern, text)
    
    if not urls:
        await message.reply_text("❌ لم أجد رابط يوتيوب صحيح في رسالتك!")
        return
    
    # التحقق من حالة المستخدم
    if user_manager.is_user_busy(user_id):
        # إضافة إلى قائمة الانتظار
        await message.reply_text(
            "⏳ *لديك طلب قيد المعالجة!*\n"
            "سيتم وضع روابطك في قائمة الانتظار.",
            parse_mode='Markdown'
        )
        
        for url in urls:
            user_manager.add_to_queue(user_id, url, message.chat_id, message.message_id)
        return
    
    # معالجة الروابط
    user_manager.set_user_busy(user_id)
    
    try:
        # إرسال رسالة بداية المعالجة
        processing_msg = await message.reply_text(
            f"⏳ جاري تحميل {len(urls)} صوت...",
            parse_mode='Markdown'
        )
        
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
                    await message.reply_text(
                        f"❌ فشل تحميل الرابط {idx}/{len(urls)}:\n`{url}`",
                        parse_mode='Markdown'
                    )
                    continue
                
                # إرسال الصوت
                with open(audio_path, 'rb') as audio_file:
                    file_size = os.path.getsize(audio_path) / (1024 * 1024)
                    
                    await message.reply_audio(
                        audio=audio_file,
                        title=title[:60] + "..." if len(title) > 60 else title,
                        performer="YouTube",
                        duration=None,
                        caption=(
                            f"🎵 *{title}*\n\n"
                            f"✅ تم التحويل بنجاح!\n"
                            f"📊 الحجم: {file_size:.1f} ميجا"
                        ),
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
                await message.reply_text(
                    f"❌ حدث خطأ في الرابط {idx}/{len(urls)}:\n`{url}`",
                    parse_mode='Markdown'
                )
        
        # تحديث رسالة المعالجة
        summary = (
            f"✅ *اكتملت المعالجة!*\n\n"
            f"✓ نجح: {success_count} صوت\n"
            f"✗ فشل: {fail_count} صوت\n"
            f"📊 إجمالي معالج اليوم: {user_manager.total_processed}"
        )
        await processing_msg.edit_text(summary, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"خطأ عام في المعالجة: {e}")
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
        
        # محاكاة طلب جديد
        class FakeUpdate:
            class Message:
                def __init__(self, chat_id, text):
                    self.chat_id = chat_id
                    self.text = text
                    self.message_id = None
            def __init__(self, chat_id, text):
                self.message = self.Message(chat_id, text)
                self.effective_user = type('User', (), {'id': user_id})()
        
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
        # عرض الإحصائيات
        stats_msg = (
            "📊 *إحصائيات البوت*\n\n"
            f"📈 إجمالي المعالجات: {user_manager.total_processed}\n"
            f"👥 المستخدمون النشطون: {len(user_manager.active_downloads)}\n"
            f"📋 الطلبات في الانتظار: {sum(len(q) for q in user_manager.user_queues.values())}"
        )
        await query.edit_message_text(stats_msg, parse_mode='Markdown')
    
    elif query.data == "help":
        help_msg = (
            "❓ *كيفية الاستخدام*\n\n"
            "1. أرسل رابط يوتيوب\n"
            "2. انتظر التحميل والتحويل\n"
            "3. استلم الصوت مباشرة\n\n"
            f"الحد الأقصى: {BotConfig.MAX_DURATION_MINUTES} دقيقة"
        )
        await query.edit_message_text(help_msg, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأخطاء العامة"""
    logger.error(f"خطأ: {context.error}")
    
    # إرسال رسالة للمستخدم إذا كان الخطأ مرتبطاً بالاستجابة
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ حدث خطأ غير متوقع. سيتم إعادة المحاولة تلقائياً."
        )

def cleanup_temp_files():
    """تنظيف الملفات المؤقتة تلقائياً"""
    try:
        now = time.time()
        for file in os.listdir(BotConfig.TEMP_FOLDER):
            file_path = os.path.join(BotConfig.TEMP_FOLDER, file)
            if os.path.isfile(file_path):
                # حذف الملفات الأقدم من ساعة
                if now - os.path.getctime(file_path) > BotConfig.CLEANUP_INTERVAL_HOURS * 3600:
                    os.remove(file_path)
                    logger.info(f"تم حذف الملف القديم: {file}")
    except Exception as e:
        logger.error(f"خطأ في التنظيف: {e}")

async def periodic_cleanup():
    """تنظيف دوري للملفات"""
    while True:
        await asyncio.sleep(BotConfig.CLEANUP_INTERVAL_HOURS * 3600)
        cleanup_temp_files()

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
        
        # تشغيل المهام الخلفية
        loop = asyncio.get_event_loop()
        loop.create_task(periodic_cleanup())
        
        # تشغيل البوت
        logger.info("🤖 البوت يعمل...")
        print(f"🤖 البوت يعمل مع المستخدم: {BOT_TOKEN[:10]}...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
        
    except Exception as e:
        logger.error(f"خطأ فادح: {e}")
        raise

if __name__ == "__main__":
    main()
