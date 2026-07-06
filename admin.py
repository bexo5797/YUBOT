import os
import shutil
import zipfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from config import Config
from database import Database
import uuid

db = Database()
MANGA_FOLDER = "manga_files"
os.makedirs(MANGA_FOLDER, exist_ok=True)

class AdminBot:
    def __init__(self):
        self.app = Application.builder().token(Config.BOT_TOKEN).build()
        self.setup_handlers()
        self.admin_states = {}  # تخزين حالة الأدمن
        
    def is_admin(self, user_id):
        return user_id in Config.ADMIN_IDS
    
    def setup_handlers(self):
        """تسجيل معالجات الأوامر"""
        # أوامر الأدمن
        self.app.add_handler(CommandHandler("admin", self.admin_panel))
        self.app.add_handler(CommandHandler("addmanga", self.add_manga_start))
        self.app.add_handler(CommandHandler("addchapter", self.add_chapter_start))
        self.app.add_handler(CommandHandler("listmanga", self.list_manga_admin))
        self.app.add_handler(CommandHandler("deletemanga", self.delete_manga_start))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        
        # معالجات الملفات
        self.app.add_handler(MessageHandler(
            filters.Document.ALL | filters.PHOTO, 
            self.handle_file_upload
        ))
        
        # معالج النصوص للأدمن
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_text_input
        ))
        
        # معالج الضغط على الأزرار
        self.app.add_handler(CallbackQueryHandler(self.handle_admin_callback))
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لوحة تحكم الأدمن"""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ غير مصرح لك باستخدام هذا الأمر.")
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة مانجا جديدة", callback_data="admin_add_manga")],
            [InlineKeyboardButton("📤 إضافة فصل جديد", callback_data="admin_add_chapter")],
            [InlineKeyboardButton("📋 عرض المانجا", callback_data="admin_list_manga")],
            [InlineKeyboardButton("🗑️ حذف مانجا", callback_data="admin_delete_manga")],
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔧 **لوحة تحكم الأدمن**\nاختر الإجراء المطلوب:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def add_manga_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء إضافة مانجا جديدة"""
        if not self.is_admin(update.effective_user.id):
            return
        
        user_id = update.effective_user.id
        self.admin_states[user_id] = {"action": "add_manga", "step": "name"}
        
        await update.message.reply_text(
            "📝 **إضافة مانجا جديدة**\n\n"
            "أرسل اسم المانجا:",
            parse_mode="Markdown"
        )
    
    async def add_chapter_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء إضافة فصل جديد"""
        if not self.is_admin(update.effective_user.id):
            return
        
        user_id = update.effective_user.id
        manga_list = db.get_manga_list()
        
        if not manga_list:
            await update.message.reply_text("❌ لا توجد مانجا. أضف مانجا أولاً.")
            return
        
        keyboard = []
        for manga in manga_list:
            keyboard.append([InlineKeyboardButton(
                f"📖 {manga['name']}",
                callback_data=f"admin_select_manga_{manga['manga_id']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📤 **إضافة فصل جديد**\nاختر المانجا:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أزرار الأدمن"""
        query = update.callback_query
        await query.answer()
        
        if not self.is_admin(update.effective_user.id):
            await query.edit_message_text("⛔ غير مصرح لك.")
            return
        
        data = query.data
        user_id = update.effective_user.id
        
        if data == "admin_add_manga":
            await self.add_manga_start(update, context)
        
        elif data == "admin_add_chapter":
            await self.add_chapter_start(update, context)
        
        elif data == "admin_list_manga":
            await self.list_manga_admin(update, context)
        
        elif data == "admin_delete_manga":
            await self.delete_manga_start(update, context)
        
        elif data == "admin_stats":
            await self.stats_command(update, context)
        
        elif data.startswith("admin_select_manga_"):
            manga_id = data.replace("admin_select_manga_", "")
            self.admin_states[user_id] = {
                "action": "add_chapter",
                "manga_id": manga_id,
                "step": "chapter_number"
            }
            await query.edit_message_text(
                f"📤 أرسل رقم الفصل (مثلاً: 1):"
            )
        
        elif data.startswith("admin_delete_confirm_"):
            manga_id = data.replace("admin_delete_confirm_", "")
            db.delete_manga(manga_id)
            
            # حذف المجلد
            manga_folder = os.path.join(MANGA_FOLDER, manga_id)
            if os.path.exists(manga_folder):
                shutil.rmtree(manga_folder)
            
            await query.edit_message_text("✅ تم حذف المانجا بنجاح.")
    
    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج النصوص للأدمن"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            return
        
        if user_id not in self.admin_states:
            return
        
        state = self.admin_states[user_id]
        text = update.message.text
        
        if state["action"] == "add_manga":
            if state["step"] == "name":
                state["name"] = text
                state["step"] = "author"
                await update.message.reply_text("✍️ أرسل اسم المؤلف:")
            
            elif state["step"] == "author":
                state["author"] = text
                state["step"] = "description"
                await update.message.reply_text("📝 أرسل وصف المانجا:")
            
            elif state["step"] == "description":
                state["description"] = text
                state["step"] = "cover"
                await update.message.reply_text(
                    "🖼️ أرسل غلاف المانجا (صورة):\n"
                    "أو اكتب 'تخطي' لتخطي هذه الخطوة."
                )
            
            elif state["step"] == "cover":
                # انتظار صورة الغلاف
                pass
        
        elif state["action"] == "add_chapter":
            if state["step"] == "chapter_number":
                try:
                    chapter_num = int(text)
                    state["chapter_number"] = chapter_num
                    state["step"] = "upload_files"
                    
                    # إنشاء مجلد للفصل
                    manga_folder = os.path.join(MANGA_FOLDER, state["manga_id"], str(chapter_num))
                    os.makedirs(manga_folder, exist_ok=True)
                    state["folder"] = manga_folder
                    state["files"] = []
                    
                    await update.message.reply_text(
                        f"📤 أرسل صور الفصل (يمكنك إرسال عدة صور متتالية).\n"
                        f"عند الانتهاء، أرسل كلمة 'تم'."
                    )
                except ValueError:
                    await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
    
    async def handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج رفع الملفات"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id) or user_id not in self.admin_states:
            return
        
        state = self.admin_states[user_id]
        
        # معالجة غلاف المانجا
        if state["action"] == "add_manga" and state["step"] == "cover":
            if update.message.photo:
                photo = update.message.photo[-1]
                file = await photo.get_file()
                
                # حفظ الغلاف
                manga_id = str(uuid.uuid4())[:8]
                state["manga_id"] = manga_id
                cover_folder = os.path.join(MANGA_FOLDER, manga_id)
                os.makedirs(cover_folder, exist_ok=True)
                cover_path = os.path.join(cover_folder, "cover.jpg")
                await file.download_to_drive(cover_path)
                
                # حفظ في قاعدة البيانات
                db.add_manga(
                    manga_id=manga_id,
                    name=state["name"],
                    author=state["author"],
                    description=state["description"],
                    cover=cover_path
                )
                
                await update.message.reply_text(
                    f"✅ تم إضافة المانجا **{state['name']}** بنجاح!\n"
                    f"🆔 معرف المانجا: `{manga_id}`",
                    parse_mode="Markdown"
                )
                
                del self.admin_states[user_id]
        
        # معالجة صور الفصل
        elif state["action"] == "add_chapter" and state["step"] == "upload_files":
            if update.message.document:
                document = update.message.document
                # التحقق من امتداد الملف
                file_ext = os.path.splitext(document.file_name)[1].lower()
                if file_ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                    await update.message.reply_text("❌ يرجى إرسال صور فقط (jpg, png, webp).")
                    return
                
                # تحميل الملف
                file = await document.get_file()
                file_path = os.path.join(state["folder"], document.file_name)
                await file.download_to_drive(file_path)
                state["files"].append(document.file_name)
                
                await update.message.reply_text(
                    f"✅ تم رفع {document.file_name}\n"
                    f"عدد الصور: {len(state['files'])}"
                )
            
            elif update.message.photo:
                photo = update.message.photo[-1]
                file = await photo.get_file()
                
                # تسمية الملف
                file_name = f"page_{len(state['files']) + 1}.jpg"
                file_path = os.path.join(state["folder"], file_name)
                await file.download_to_drive(file_path)
                state["files"].append(file_name)
                
                await update.message.reply_text(
                    f"✅ تم رفع الصورة {len(state['files'])}"
                )
            
            elif update.message.text and update.message.text.lower() == "تم":
                # إنهاء رفع الفصل
                if not state["files"]:
                    await update.message.reply_text("❌ لم تقم برفع أي صور.")
                    return
                
                db.add_chapter(
                    manga_id=state["manga_id"],
                    chapter_number=state["chapter_number"],
                    files=state["files"]
                )
                
                await update.message.reply_text(
                    f"✅ تم إضافة الفصل {state['chapter_number']} بنجاح!\n"
                    f"عدد الصور: {len(state['files'])}"
                )
                
                del self.admin_states[user_id]
    
    async def list_manga_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة المانجا للأدمن"""
        if not self.is_admin(update.effective_user.id):
            return
        
        manga_list = db.get_manga_list()
        
        if not manga_list:
            await update.message.reply_text("📭 لا توجد مانجا.")
            return
        
        text = "📋 **قائمة المانجا:**\n\n"
        for manga in manga_list:
            chapters = db.get_chapters(manga['manga_id'])
            text += f"📖 {manga['name']} - {len(chapters)} فصل\n"
            text += f"🆔 `{manga['manga_id']}`\n\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def delete_manga_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية حذف مانجا"""
        if not self.is_admin(update.effective_user.id):
            return
        
        manga_list = db.get_manga_list()
        
        if not manga_list:
            await update.message.reply_text("❌ لا توجد مانجا لحذفها.")
            return
        
        keyboard = []
        for manga in manga_list:
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {manga['name']}",
                callback_data=f"admin_delete_confirm_{manga['manga_id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data="admin_cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ **حذف مانجا**\nاختر المانجا التي تريد حذفها:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إحصائيات البوت"""
        if not self.is_admin(update.effective_user.id):
            return
        
        user_count = db.get_user_count()
        manga_count = len(db.get_manga_list())
        
        # حساب عدد الفصول
        all_manga = db.get_manga_list()
        total_chapters = 0
        for manga in all_manga:
            total_chapters += len(db.get_chapters(manga['manga_id']))
        
        text = f"""
📊 **إحصائيات البوت**

👥 عدد المستخدمين: {user_count}
📚 عدد المانجا: {manga_count}
📖 عدد الفصول: {total_chapters}

📁 المساحة المستخدمة: {self.get_folder_size(MANGA_FOLDER)}
        """
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    def get_folder_size(self, folder):
        """حساب حجم المجلد"""
        total = 0
        for path, dirs, files in os.walk(folder):
            for f in files:
                fp = os.path.join(path, f)
                total += os.path.getsize(fp)
        
        if total < 1024:
            return f"{total} B"
        elif total < 1024 * 1024:
            return f"{total/1024:.2f} KB"
        else:
            return f"{total/(1024*1024):.2f} MB"
    
    def run(self):
        """تشغيل البوت"""
        print("🤖 بوت الأدمن يعمل...")
        self.app.run_polling()

if __name__ == "__main__":
    bot = AdminBot()
    bot.run()
