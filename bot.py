import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from PIL import Image
from io import BytesIO
import subprocess
import shutil
from datetime import datetime

# توكن البوت
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
os.makedirs("packs", exist_ok=True)

# ملف لحفظ بيانات الحزم
PACKS_FILE = "packs_data.json"

def load_packs():
    if os.path.exists(PACKS_FILE):
        try:
            with open(PACKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_packs(packs):
    try:
        with open(PACKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(packs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")

packs_data = load_packs()
user_pack_queue = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📸 صورة → ملصق", callback_data='photo')],
        [InlineKeyboardButton("🎬 فيديو → ملصق متحرك", callback_data='video')],
        [InlineKeyboardButton("📦 إنشاء حزمة ملصقات", callback_data='create_pack')],
        [InlineKeyboardButton("📚 حزمي", callback_data='my_packs')],
        [InlineKeyboardButton("❓ المساعدة", callback_data='help')]
    ]
    await update.message.reply_text(
        "👋 أهلاً بك في بوت الملصقات!\n\n"
        "📸 أرسل صورة لصنع ملصق عادي\n"
        "🎬 أرسل فيديو لصنع ملصق متحرك\n"
        "📦 أنشئ حزمة ملصقات خاصة بك\n\n"
        "✨ اختر ما تريد:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.message.from_user.id)
        
        if not update.message.photo:
            await update.message.reply_text("❌ لم أجد صورة! أرسل صورة من فضلك.")
            return
        
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        image_data = await file.download_as_bytearray()
        img = Image.open(BytesIO(image_data))
        img = img.resize((512, 512))
        
        filename = f"sticker_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join("stickers", filename)
        img.save(path, "PNG")
        
        with open(path, 'rb') as f:
            await update.message.reply_sticker(f)
        
        try:
            os.remove(path)
        except:
            pass
        
        keyboard = [
            [InlineKeyboardButton("🔄 ملصق جديد", callback_data='photo')],
            [InlineKeyboardButton("📦 إضافة للحزمة", callback_data='create_pack')]
        ]
        await update.message.reply_text(
            "✅ تم صنع الملصق بنجاح!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الصورة: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)[:50]}")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.message.from_user.id)
        
        if not update.message.video:
            await update.message.reply_text("❌ لم أجد فيديو! أرسل فيديو من فضلك.")
            return
        
        video = update.message.video
        
        if video.file_size > 20 * 1024 * 1024:
            await update.message.reply_text("❌ الفيديو كبير جداً! الحد الأقصى 20 ميجابايت.")
            return
        
        file = await context.bot.get_file(video.file_id)
        video_data = await file.download_as_bytearray()
        
        temp_filename = f"temp_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        temp_path = os.path.join("videos", temp_filename)
        
        with open(temp_path, "wb") as f:
            f.write(video_data)
        
        webp_filename = f"sticker_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webp"
        webp_path = os.path.join("stickers", webp_filename)
        
        if not shutil.which('ffmpeg'):
            await update.message.reply_text("❌ البوت يحتاج إلى FFmpeg للتشغيل!")
            return
        
        # ✅ الأمر الصحيح لتحويل فيديو إلى ملصق متحرك (WebP)
        cmd = [
            "ffmpeg", "-i", temp_path,
            "-vf", "fps=15,scale=512:512:flags=lanczos",  # زيادة FPS للحركة
            "-loop", "0",  # تكرار غير محدود
            "-c:v", "libwebp",  # ترميز WebP
            "-lossless", "0",  # ضغط مع فقدان
            "-q:v", "80",  # جودة عالية
            "-preset", "default",
            "-y",
            webp_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            await update.message.reply_text("❌ فشل تحويل الفيديو. تأكد من صيغة MP4.")
            try:
                os.remove(temp_path)
            except:
                pass
            return
        
        if not os.path.exists(webp_path) or os.path.getsize(webp_path) == 0:
            await update.message.reply_text("❌ فشل إنشاء الملصق المتحرك.")
            try:
                os.remove(temp_path)
            except:
                pass
            return
        
        # إرسال الملصق المتحرك
        with open(webp_path, 'rb') as f:
            await update.message.reply_sticker(f)
        
        # حذف الملفات المؤقتة
        try:
            os.remove(temp_path)
            os.remove(webp_path)
        except:
            pass
        
        keyboard = [
            [InlineKeyboardButton("🔄 ملصق جديد", callback_data='video')],
            [InlineKeyboardButton("📦 إضافة للحزمة", callback_data='create_pack')]
        ]
        await update.message.reply_text(
            "✅ تم صنع الملصق المتحرك بنجاح! 🎬",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الفيديو: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)[:50]}")

async def create_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # التعامل مع callback أو message
        if hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            await query.answer()
            user_id = str(query.from_user.id)
            message = query.message
        else:
            user_id = str(update.effective_user.id)
            message = update.message
        
        user_pack_queue[user_id] = {"step": "name", "stickers": []}
        
        keyboard = [
            [InlineKeyboardButton("❌ إلغاء", callback_data='cancel_pack')]
        ]
        
        await message.reply_text(
            "📝 **أدخل اسم الحزمة**\n\n"
            "أرسل لي اسم الحزمة (مثال: 'حزمة مضحكة' أو 'Fun Pack'):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء الحزمة: {e}")
        if hasattr(update, 'callback_query'):
            await update.callback_query.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")
        else:
            await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")

async def handle_pack_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.message.from_user.id)
        pack_name = update.message.text
        
        if user_id not in user_pack_queue:
            await update.message.reply_text("❌ لم تبدأ عملية إنشاء حزمة. استخدم /start")
            return
        
        user_pack_queue[user_id]["name"] = pack_name
        user_pack_queue[user_id]["step"] = "stickers"
        
        await update.message.reply_text(
            f"✅ اسم الحزمة: **{pack_name}**\n\n"
            "📤 الآن أرسل لي **الصور** أو **الفيديوهات** لإضافتها للحزمة.\n"
            "يمكنك إرسال عدة ملفات.\n\n"
            "عند الانتهاء، أرسل كلمة **/done**"
        )
    except Exception as e:
        logger.error(f"خطأ في اسم الحزمة: {e}")
        await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")

async def add_sticker_to_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.message.from_user.id)
        
        if user_id not in user_pack_queue or user_pack_queue[user_id].get("step") != "stickers":
            await update.message.reply_text("❌ ليس في وضع إضافة ملصقات. استخدم /start")
            return
        
        # معالجة الصورة
        if update.message.photo:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            # حفظ معرف الملف
            sticker_file_id = file.file_id
            user_pack_queue[user_id]["stickers"].append(sticker_file_id)
            
            await update.message.reply_text(
                f"✅ تم إضافة الملصق!\n"
                f"📊 العدد الحالي: {len(user_pack_queue[user_id]['stickers'])}"
            )
        
        # معالجة الفيديو
        elif update.message.video:
            video = update.message.video
            file = await context.bot.get_file(video.file_id)
            
            sticker_file_id = file.file_id
            user_pack_queue[user_id]["stickers"].append(sticker_file_id)
            
            await update.message.reply_text(
                f"✅ تم إضافة الملصق المتحرك!\n"
                f"📊 العدد الحالي: {len(user_pack_queue[user_id]['stickers'])}"
            )
        
        else:
            await update.message.reply_text("❌ أرسل صورة أو فيديو فقط!")
            
    except Exception as e:
        logger.error(f"خطأ في إضافة الملصق: {e}")
        await update.message.reply_text("❌ حدث خطأ!")

async def finish_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.message.from_user.id)
        
        if user_id not in user_pack_queue:
            await update.message.reply_text("❌ لا توجد حزمة قيد الإنشاء!")
            return
        
        pack_data = user_pack_queue[user_id]
        pack_name = pack_data.get("name", f"حزمة {user_id}")
        stickers = pack_data.get("stickers", [])
        
        if not stickers:
            await update.message.reply_text("❌ لا توجد ملصقات في الحزمة! أرسل بعض الملصقات أولاً.")
            return
        
        # إنشاء معرف الحزمة
        pack_id = f"pack_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # حفظ البيانات
        packs_data[pack_id] = {
            "name": pack_name,
            "user_id": user_id,
            "stickers": stickers,
            "created_at": datetime.now().isoformat(),
            "count": len(stickers)
        }
        save_packs(packs_data)
        
        # رابط الحزمة
        pack_link = f"https://t.me/addstickers/{pack_id}"
        
        keyboard = [
            [InlineKeyboardButton("📤 مشاركة الحزمة", url=f"https://t.me/share/url?url={pack_link}&text=🎨 حزمة ملصقات جديدة!")],
            [InlineKeyboardButton("📚 حزمي", callback_data='my_packs')],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu')]
        ]
        
        await update.message.reply_text(
            f"✅ **تم إنشاء الحزمة بنجاح!**\n\n"
            f"📦 الاسم: {pack_name}\n"
            f"📊 عدد الملصقات: {len(stickers)}\n"
            f"🔗 الرابط:\n{pack_link}\n\n"
            f"شارك الرابط مع أصدقائك! 🎉",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # تنظيف
        del user_pack_queue[user_id]
        
    except Exception as e:
        logger.error(f"خطأ في إنهاء الحزمة: {e}")
        await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")

async def my_packs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        
        user_packs = {pid: data for pid, data in packs_data.items() if data.get("user_id") == user_id}
        
        if not user_packs:
            await update.message.reply_text(
                "📭 ليس لديك أي حزم ملصقات حتى الآن.\n"
                "استخدم /start ثم اضغط 'إنشاء حزمة ملصقات'"
            )
            return
        
        keyboard = []
        for pack_id, pack_data in user_packs.items():
            pack_link = f"https://t.me/addstickers/{pack_id}"
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 {pack_data.get('name', 'بدون اسم')} ({pack_data.get('count', 0)})",
                    url=pack_link
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu')])
        
        await update.message.reply_text(
            "📚 **حزم الملصقات الخاصة بك:**\n\n"
            "اضغط على أي حزمة لفتحها:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"خطأ في عرض الحزم: {e}")
        await update.message.reply_text("❌ حدث خطأ!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'photo':
            await query.message.reply_text("📸 أرسل الصورة الآن:")
        
        elif query.data == 'video':
            await query.message.reply_text("🎬 أرسل الفيديو الآن (MP4):")
        
        elif query.data == 'create_pack':
            # استدعاء دالة إنشاء الحزمة مع تمرير callback
            await create_pack(update, context)
        
        elif query.data == 'my_packs':
            await my_packs(update, context)
        
        elif query.data == 'help':
            await query.message.reply_text(
                "❓ **كيفية الاستخدام:**\n\n"
                "📸 **صنع ملصق:**\n"
                "• أرسل صورة → ملصق عادي\n"
                "• أرسل فيديو MP4 → ملصق متحرك\n\n"
                "📦 **حزم الملصقات:**\n"
                "1. اضغط 'إنشاء حزمة'\n"
                "2. أدخل اسم الحزمة\n"
                "3. أرسل الصور أو الفيديوهات\n"
                "4. اضغط /done للانتهاء\n\n"
                "📚 **عرض حزمي:**\n"
                "يعرض جميع الحزم التي أنشأتها"
            )
        
        elif query.data == 'main_menu':
            await start(update, context)
        
        elif query.data == 'cancel_pack':
            user_id = str(query.from_user.id)
            if user_id in user_pack_queue:
                del user_pack_queue[user_id]
            await query.message.reply_text("❌ تم إلغاء إنشاء الحزمة.")
            
    except Exception as e:
        logger.error(f"خطأ في معالج الأزرار: {e}")
        await query.message.reply_text("❌ حدث خطأ!")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.message.from_user.id)
        text = update.message.text
        
        if text == '/done':
            await finish_pack(update, context)
        elif user_id in user_pack_queue and user_pack_queue[user_id].get("step") == "name":
            await handle_pack_name(update, context)
        else:
            await update.message.reply_text(
                "❌ لم أفهم! استخدم الأزرار أو أرسل صورة/فيديو."
            )
    except Exception as e:
        logger.error(f"خطأ في معالج النصوص: {e}")
        await update.message.reply_text("❌ حدث خطأ!")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"خطأ: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ حدث خطأ غير متوقع. حاول مرة أخرى.")
    except:
        pass

def main():
    app = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", finish_pack))
    app.add_handler(MessageHandler(filters.PHOTO, add_sticker_to_pack))
    app.add_handler(MessageHandler(filters.VIDEO, add_sticker_to_pack))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    
    logger.info("🤖 البوت يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
