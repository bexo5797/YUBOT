import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Sticker
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from PIL import Image
from io import BytesIO
import subprocess
import shutil
import zipfile
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

# تحميل بيانات الحزم
def load_packs():
    if os.path.exists(PACKS_FILE):
        with open(PACKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# حفظ بيانات الحزم
def save_packs(packs):
    with open(PACKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(packs, f, ensure_ascii=False, indent=2)

packs_data = load_packs()

# قائمة انتظار لإنشاء الحزمة
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
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        
        # تحويل الصورة
        img = Image.open(BytesIO(await file.download_as_bytearray()))
        img = img.resize((512, 512))
        
        path = f"stickers/{user_id}_{datetime.now().timestamp()}.png"
        img.save(path, "PNG")
        
        # إرسال الملصق
        with open(path, 'rb') as f:
            message = await update.message.reply_sticker(f)
        
        # حفظ معرف الملصق
        sticker_file_id = message.sticker.file_id
        
        keyboard = [
            [InlineKeyboardButton("📦 إضافة إلى حزمة", callback_data=f'add_to_pack_{sticker_file_id}_{path}')],
            [InlineKeyboardButton("🔄 ملصق جديد", callback_data='photo')]
        ]
        await update.message.reply_text(
            "✅ تم صنع الملصق!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"خطأ في الصورة: {e}")
        await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.message.from_user.id)
        file = await context.bot.get_file(update.message.video.file_id)
        
        if update.message.video.file_size > 20 * 1024 * 1024:
            await update.message.reply_text("❌ الفيديو كبير جداً! الحد الأقصى 20 ميجابايت.")
            return
        
        # تحميل الفيديو
        temp = f"videos/{user_id}_{datetime.now().timestamp()}.mp4"
        with open(temp, "wb") as f:
            f.write(await file.download_as_bytearray())
        
        # تحويل إلى WebP
        webp = f"stickers/{user_id}_{datetime.now().timestamp()}.webp"
        
        if not shutil.which('ffmpeg'):
            await update.message.reply_text("❌ FFmpeg غير مثبت!")
            return
        
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
        
        subprocess.run(cmd, capture_output=True, text=True)
        
        if os.path.exists(webp):
            with open(webp, 'rb') as f:
                message = await update.message.reply_sticker(f)
            
            sticker_file_id = message.sticker.file_id
            
            keyboard = [
                [InlineKeyboardButton("📦 إضافة إلى حزمة", callback_data=f'add_to_pack_{sticker_file_id}_{webp}')],
                [InlineKeyboardButton("🔄 ملصق جديد", callback_data='video')]
            ]
            await update.message.reply_text(
                "✅ تم صنع الملصق المتحرك!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            os.remove(temp)
            os.remove(webp)
        else:
            await update.message.reply_text("❌ فشل تحويل الفيديو.")
            
    except Exception as e:
        logger.error(f"خطأ في الفيديو: {e}")
        await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")

async def create_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    keyboard = [
        [InlineKeyboardButton("📝 إدخال اسم الحزمة", callback_data='name_pack')],
        [InlineKeyboardButton("❌ إلغاء", callback_data='cancel_pack')]
    ]
    await update.message.reply_text(
        "📦 **إنشاء حزمة ملصقات جديدة**\n\n"
        "سأرسل لك تعليمات لإنشاء الحزمة.\n"
        "اضغط على الزر أدناه لإدخال اسم الحزمة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_pack_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    user_pack_queue[user_id] = {"step": "name", "stickers": []}
    
    await query.message.reply_text(
        "📝 أرسل لي اسم الحزمة (باللغة العربية أو الإنجليزية):"
    )

async def handle_pack_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    pack_name = update.message.text
    
    if user_id not in user_pack_queue:
        await update.message.reply_text("❌ لم تبدأ عملية إنشاء حزمة. استخدم /start")
        return
    
    user_pack_queue[user_id]["name"] = pack_name
    user_pack_queue[user_id]["step"] = "stickers"
    
    # إرسال 5 ملصقات افتراضية للاختبار
    await update.message.reply_text(
        f"✅ اسم الحزمة: **{pack_name}**\n\n"
        "📤 الآن أرسل لي الملصقات التي تريد إضافتها.\n"
        "يمكنك إرسال صور أو فيديوهات.\n"
        "عند الانتهاء، أرسل كلمة **/done**"
    )

async def add_to_pack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data.replace('add_to_pack_', '')
    sticker_file_id, file_path = data.split('_', 1)
    
    if user_id not in user_pack_queue:
        user_pack_queue[user_id] = {"step": "stickers", "stickers": []}
    
    user_pack_queue[user_id]["stickers"].append(sticker_file_id)
    
    await query.message.reply_text(
        f"✅ تم إضافة الملصق إلى الحزمة!\n"
        f"العدد الحالي: {len(user_pack_queue[user_id]['stickers'])}"
    )

async def finish_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if user_id not in user_pack_queue or not user_pack_queue[user_id].get("stickers"):
        await update.message.reply_text("❌ لا توجد ملصقات في الحزمة!")
        return
    
    pack_data = user_pack_queue[user_id]
    pack_name = pack_data.get("name", f"حزمة {user_id}")
    stickers = pack_data["stickers"]
    
    # إنشاء معرف الحزمة
    pack_id = f"pack_{user_id}_{datetime.now().timestamp()}"
    
    # حفظ البيانات
    packs_data[pack_id] = {
        "name": pack_name,
        "user_id": user_id,
        "stickers": stickers,
        "created_at": datetime.now().isoformat(),
        "count": len(stickers)
    }
    save_packs(packs_data)
    
    # إرسال رابط الحزمة
    pack_link = f"https://t.me/addstickers/{pack_id}"
    
    keyboard = [
        [InlineKeyboardButton("📤 مشاركة الحزمة", url=f"https://t.me/share/url?url={pack_link}&text=🎨 حزمة ملصقات جديدة!")],
        [InlineKeyboardButton("📋 نسخ الرابط", callback_data=f'copy_link_{pack_id}')],
        [InlineKeyboardButton("📚 حزمي", callback_data='my_packs')]
    ]
    
    await update.message.reply_text(
        f"✅ **تم إنشاء الحزمة بنجاح!**\n\n"
        f"📦 الاسم: {pack_name}\n"
        f"📊 عدد الملصقات: {len(stickers)}\n"
        f"🔗 الرابط: {pack_link}\n\n"
        f"شارك الرابط مع أصدقائك!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # تنظيف
    del user_pack_queue[user_id]

async def my_packs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    user_packs = {pid: data for pid, data in packs_data.items() if data["user_id"] == user_id}
    
    if not user_packs:
        await update.message.reply_text(
            "📭 ليس لديك أي حزم ملصقات حتى الآن.\n"
            "استخدم /start لإنشاء حزمة جديدة."
        )
        return
    
    keyboard = []
    for pack_id, pack_data in user_packs.items():
        pack_link = f"https://t.me/addstickers/{pack_id}"
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {pack_data['name']} ({pack_data['count']})",
                url=pack_link
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔄 تحديث", callback_data='my_packs')])
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu')])
    
    await update.message.reply_text(
        "📚 **حزم الملصقات الخاصة بك:**\n\n"
        "اضغط على أي حزمة لعرضها:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'photo':
        await query.message.reply_text("📸 أرسل الصورة الآن:")
    
    elif query.data == 'video':
        await query.message.reply_text("🎬 أرسل الفيديو الآن:")
    
    elif query.data == 'create_pack':
        await start_pack_creation(update)
    
    elif query.data == 'my_packs':
        await my_packs(update, context)
    
    elif query.data == 'help':
        await query.message.reply_text(
            "❓ **كيفية الاستخدام:**\n\n"
            "📸 **صنع ملصق:**\n"
            "• أرسل صورة → ملصق عادي\n"
            "• أرسل فيديو → ملصق متحرك\n\n"
            "📦 **حزم الملصقات:**\n"
            "1. اضغط 'إنشاء حزمة'\n"
            "2. أدخل اسم الحزمة\n"
            "3. أرسل الملصقات\n"
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
    
    elif query.data.startswith('copy_link_'):
        pack_id = query.data.replace('copy_link_', '')
        pack_link = f"https://t.me/addstickers/{pack_id}"
        await query.message.reply_text(f"🔗 رابط الحزمة:\n{pack_link}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text
    
    if text == '/done':
        await finish_pack(update, context)
    elif user_id in user_pack_queue and user_pack_queue[user_id].get("step") == "name":
        await handle_pack_name(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"خطأ: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ حدث خطأ غير متوقع. حاول مرة أخرى.")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", finish_pack))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    
    logger.info("🤖 البوت يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
