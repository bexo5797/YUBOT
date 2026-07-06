import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from PIL import Image
from io import BytesIO
import subprocess
import shutil

# توكن البوت من متغيرات البيئة
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود!")

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
        [InlineKeyboardButton("📸 صورة → ملصق", callback_data='photo')],
        [InlineKeyboardButton("🎬 فيديو → ملصق متحرك", callback_data='video')],
        [InlineKeyboardButton("❓ المساعدة", callback_data='help')]
    ]
    await update.message.reply_text(
        "👋 أهلاً بك في بوت الملصقات!\n\n"
        "📸 أرسل صورة لصنع ملصق عادي\n"
        "🎬 أرسل فيديو لصنع ملصق متحرك (WebP)\n\n"
        "✨ جميع الملصقات تأتي مع رابط مشاركة للواتساب",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        
        # تحميل وتحويل الصورة
        img = Image.open(BytesIO(await file.download_as_bytearray()))
        img = img.resize((512, 512))
        
        path = f"stickers/{user_id}.png"
        img.save(path, "PNG")
        
        # إرسال الملصق
        with open(path, 'rb') as f:
            await update.message.reply_sticker(f)
        
        os.remove(path)
        
        # رابط واتساب
        keyboard = [[
            InlineKeyboardButton("📱 مشاركة واتساب", url="https://api.whatsapp.com/send?text=🎨 ملصق جديد من بوت الملصقات!")
        ]]
        await update.message.reply_text(
            "✅ تم صنع الملصق! شاركه الآن:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"خطأ في الصورة: {e}")
        await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        file = await context.bot.get_file(update.message.video.file_id)
        
        # التحقق من حجم الفيديو
        if update.message.video.file_size > 20 * 1024 * 1024:
            await update.message.reply_text("❌ الفيديو كبير جداً! الحد الأقصى 20 ميجابايت.")
            return
        
        # تحميل الفيديو
        temp = f"videos/{user_id}.mp4"
        with open(temp, "wb") as f:
            f.write(await file.download_as_bytearray())
        
        # تحويل إلى WebP متحرك
        webp = f"stickers/{user_id}.webp"
        
        if not shutil.which('ffmpeg'):
            await update.message.reply_text("❌ FFmpeg غير مثبت!")
            return
        
        # أمر تحويل الفيديو
        cmd = [
            "ffmpeg", "-i", temp,
            "-vf", "fps=10,scale=512:512:flags=lanczos",
            "-t", "3",
            "-loop", "0",
            "-c:v", "libwebp",
            "-lossless", "0",
            "-q:v", "70",
            "-y",
            webp
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            await update.message.reply_text("❌ فشل تحويل الفيديو. تأكد من الصيغة.")
            return
        
        # إرسال الملصق المتحرك
        if os.path.exists(webp):
            with open(webp, 'rb') as f:
                await update.message.reply_sticker(f)
            os.remove(webp)
        
        os.remove(temp)
        
        # رابط واتساب
        keyboard = [[
            InlineKeyboardButton("📱 مشاركة واتساب", url="https://api.whatsapp.com/send?text=🎬 ملصق متحرك من بوت الملصقات!")
        ]]
        await update.message.reply_text(
            "✅ تم صنع الملصق المتحرك! شاركه الآن:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"خطأ في الفيديو: {e}")
        await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help':
        await query.message.reply_text(
            "❓ **كيفية الاستخدام:**\n\n"
            "1️⃣ أرسل صورة → ملصق عادي\n"
            "2️⃣ أرسل فيديو → ملصق متحرك\n"
            "3️⃣ اضغط واتساب للمشاركة\n\n"
            "📌 **النصائح:**\n"
            "• فيديو قصير (3-5 ثواني)\n"
            "• صيغة MP4 أو MOV\n"
            "• حجم أقل من 20 ميجابايت"
        )
    else:
        await query.message.reply_text("📤 أرسل الملف الآن:")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"خطأ: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ حدث خطأ غير متوقع. حاول مرة أخرى.")

def main():
    # إنشاء التطبيق
    app = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    
    # تشغيل البوت
    logger.info("🤖 البوت يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
