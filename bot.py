import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from PIL import Image
import requests
from io import BytesIO
import base64
import subprocess
import tempfile
import shutil

# توكن البوت من متغيرات البيئة
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ لم يتم تعيين BOT_TOKEN في متغيرات البيئة!")

# تفعيل التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إنشاء المجلدات
os.makedirs("stickers", exist_ok=True)
os.makedirs("videos", exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📸 ملصق من صورة", callback_data='photo_sticker')],
        [InlineKeyboardButton("🎬 ملصق من فيديو", callback_data='video_sticker')],
        [InlineKeyboardButton("❓ المساعدة", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 أهلاً بك في بوت الملصقات!\n\n"
        "اختر نوع الملصق:\n"
        "📸 صورة → ملصق عادي\n"
        "🎬 فيديو → ملصق متحرك (WebP)\n\n"
        "✨ جميع الملصقات تأتي مع رابط مشاركة للواتساب",
        reply_markup=reply_markup
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    photo = update.message.photo[-1]
    
    try:
        # تحميل الصورة
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        
        # تحويل إلى ملصق
        img = Image.open(BytesIO(image_bytes))
        img = img.resize((512, 512))
        
        # حفظ الملصق
        sticker_path = f"stickers/{user.id}.png"
        img.save(sticker_path, "PNG")
        
        # إرسال الملصق
        with open(sticker_path, 'rb') as f:
            await update.message.reply_sticker(f)
        
        # رابط واتساب
        whatsapp_link = "https://api.whatsapp.com/send?text=🎨 ملصق جديد من بوت الملصقات!"
        
        keyboard = [
            [InlineKeyboardButton("📱 مشاركة عبر واتساب", url=whatsapp_link)],
            [InlineKeyboardButton("🔄 ملصق جديد", callback_data='new_sticker')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ تم صنع الملصق بنجاح!", reply_markup=reply_markup)
        
        # تنظيف
        os.remove(sticker_path)
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الصورة: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء معالجة الصورة. حاول مرة أخرى.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    video = update.message.video
    
    # التحقق من حجم الفيديو
    if video.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("❌ الفيديو كبير جداً! الحد الأقصى 20 ميجابايت.")
        return
    
    try:
        # تحميل الفيديو
        file = await context.bot.get_file(video.file_id)
        video_bytes = await file.download_as_bytearray()
        
        # حفظ الفيديو مؤقتاً
        temp_video = f"videos/{user.id}.mp4"
        with open(temp_video, "wb") as f:
            f.write(video_bytes)
        
        # تحويل الفيديو إلى ملصق متحرك (WebP)
        sticker_path = f"stickers/{user.id}.webp"
        
        # التحقق من وجود ffmpeg
        if not shutil.which('ffmpeg'):
            await update.message.reply_text("❌ البوت غير مهيأ بشكل صحيح. يرجى التواصل مع المطور.")
            return
        
        # استخدام ffmpeg
        cmd = [
            "ffmpeg", "-i", temp_video,
            "-vf", "fps=10,scale=512:512:flags=lanczos",
            "-loop", "0",
            "-c:v", "libwebp",
            "-lossless", "0",
            "-q:v", "70",
            "-t", "3",
            "-y",
            sticker_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            await update.message.reply_text("❌ حدث خطأ في تحويل الفيديو.")
            return
        
        # إرسال الملصق المتحرك
        with open(sticker_path, 'rb') as f:
            await update.message.reply_sticker(f)
        
        # رابط واتساب
        whatsapp_link = "https://api.whatsapp.com/send?text=🎬 ملصق متحرك جديد من بوت الملصقات!"
        
        keyboard = [
            [InlineKeyboardButton("📱 مشاركة عبر واتساب", url=whatsapp_link)],
            [InlineKeyboardButton("🔄 ملصق جديد", callback_data='new_sticker')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ تم صنع الملصق المتحرك بنجاح!", reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الفيديو: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء معالجة الفيديو.")
    
    finally:
        # تنظيف الملفات المؤقتة
        if os.path.exists(temp_video):
            os.remove(temp_video)
        if os.path.exists(sticker_path):
            os.remove(sticker_path)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'photo_sticker':
        await query.message.reply_text("📸 أرسل لي صورة الآن لصنع ملصق.")
    
    elif query.data == 'video_sticker':
        await query.message.reply_text(
            "🎬 أرسل لي فيديو الآن.\n\n"
            "📌 **نصائح:**\n"
            "• فيديو قصير (3-5 ثواني)\n"
            "• صيغة MP4 أو MOV\n"
            "• حجم أقل من 20 ميجابايت"
        )
    
    elif query.data == 'help':
        await query.message.reply_text(
            "❓ **كيفية الاستخدام:**\n\n"
            "📸 **من صورة:**\n"
            "1️⃣ أرسل صورة\n"
            "2️⃣ يحولها لملصق عادي\n\n"
            "🎬 **من فيديو:**\n"
            "1️⃣ أرسل فيديو (MP4/MOV)\n"
            "2️⃣ يحوله لملصق متحرك (WebP)\n\n"
            "📱 **مشاركة واتساب:**\n"
            "اضغط على زر 'مشاركة عبر واتساب'\n\n"
            "⚠️ **ملاحظات:**\n"
            "• الفيديو يقتص على 3 ثواني\n"
            "• دقة الملصق: 512×512\n"
            "• الحد الأقصى للفيديو: 20 ميجابايت"
        )
    
    elif query.data == 'new_sticker':
        await query.message.reply_text(
            "🔄 اختر نوع الملصق الجديد:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📸 من صورة", callback_data='photo_sticker')],
                [InlineKeyboardButton("🎬 من فيديو", callback_data='video_sticker')]
            ])
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"خطأ: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ حدث خطأ غير متوقع. حاول مرة أخرى.")

def main():
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    
    # تشغيل البوت باستخدام polling (أسهل وأكثر استقراراً)
    logger.info("🤖 بدء تشغيل البوت باستخدام Polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
