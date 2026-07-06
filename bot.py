import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import Config
from database import Database
import aiofiles
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

db = Database()
MANGA_FOLDER = "manga_files"
os.makedirs(MANGA_FOLDER, exist_ok=True)

class MangaBot:
    def __init__(self):
        self.app = Application.builder().token(Config.BOT_TOKEN).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        """تسجيل معالجات الأوامر"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("manga", self.manga_list_command))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /start"""
        user = update.effective_user
        db.add_user(user.id, user.username)
        
        welcome_text = f"""
🎌 **مرحباً بك في بوت المانجا!**

مرحباً {user.first_name}! يمكنك مشاهدة المانجا المفضلة لديك من خلال هذا البوت.

📚 **الأوامر المتاحة:**
/manga - عرض قائمة المانجا المتاحة
/start - إعادة تشغيل البوت

💡 اختر المانجا التي تريد مشاهدتها من قائمة /manga
        """
        
        await update.message.reply_text(welcome_text, parse_mode="Markdown")
    
    async def manga_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة المانجا المتاحة"""
        manga_list = db.get_manga_list()
        
        if not manga_list:
            await update.message.reply_text("📭 لا توجد مانجا متاحة حالياً.")
            return
        
        keyboard = []
        for manga in manga_list:
            button = InlineKeyboardButton(
                f"📖 {manga['name']} - {manga.get('author', 'مؤلف غير معروف')}",
                callback_data=f"manga_{manga['manga_id']}"
            )
            keyboard.append([button])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📚 **قائمة المانجا المتاحة:**\nاختر المانجا التي تريد مشاهدتها:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الضغط على الأزرار"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("manga_"):
            manga_id = data.replace("manga_", "")
            await self.show_manga_detail(query, manga_id)
        
        elif data.startswith("chapter_"):
            _, manga_id, chapter_num = data.split("_")
            await self.show_chapter(query, manga_id, int(chapter_num))
    
    async def show_manga_detail(self, query, manga_id):
        """عرض تفاصيل المانجا والفصول"""
        manga = db.get_manga(manga_id)
        if not manga:
            await query.edit_message_text("❌ المانجا غير موجودة.")
            return
        
        chapters = db.get_chapters(manga_id)
        
        text = f"""
📖 **{manga['name']}**
✍️ المؤلف: {manga.get('author', 'غير معروف')}
📝 الوصف: {manga.get('description', 'لا يوجد وصف')}
📚 عدد الفصول: {len(chapters)}
        """
        
        keyboard = []
        # إضافة أزرار الفصول (كل 5 فصول في صف)
        for i, chapter in enumerate(chapters):
            if i % 5 == 0:
                row = []
            row.append(InlineKeyboardButton(
                f"فصل {chapter['chapter']}",
                callback_data=f"chapter_{manga_id}_{chapter['chapter']}"
            ))
            if len(row) == 5 or i == len(chapters) - 1:
                keyboard.append(row)
        
        # زر العودة للقائمة
        keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_list")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    async def show_chapter(self, query, manga_id, chapter_num):
        """عرض فصل المانجا"""
        chapter = db.get_chapter(manga_id, chapter_num)
        if not chapter:
            await query.edit_message_text("❌ الفصل غير موجود.")
            return
        
        manga = db.get_manga(manga_id)
        files = chapter.get("files", [])
        
        if not files:
            await query.edit_message_text("❌ لا توجد صور لهذا الفصل.")
            return
        
        # إرسال الصور كألبوم
        media_group = []
        for file_name in files[:10]:  # حد 10 صور لكل رسالة
            file_path = os.path.join(MANGA_FOLDER, manga_id, str(chapter_num), file_name)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    media_group.append(InputMediaPhoto(f))
        
        if media_group:
            await query.message.reply_media_group(media_group)
        
        # أزرار التنقل بين الفصول
        chapters = db.get_chapters(manga_id)
        current_index = next((i for i, ch in enumerate(chapters) if ch['chapter'] == chapter_num), -1)
        
        keyboard = []
        nav_buttons = []
        
        if current_index > 0:
            prev_chapter = chapters[current_index - 1]['chapter']
            nav_buttons.append(InlineKeyboardButton(
                "⏮️ السابق",
                callback_data=f"chapter_{manga_id}_{prev_chapter}"
            ))
        
        nav_buttons.append(InlineKeyboardButton(
            "📚 القائمة",
            callback_data=f"manga_{manga_id}"
        ))
        
        if current_index < len(chapters) - 1:
            next_chapter = chapters[current_index + 1]['chapter']
            nav_buttons.append(InlineKeyboardButton(
                "التالي ⏭️",
                callback_data=f"chapter_{manga_id}_{next_chapter}"
            ))
        
        keyboard.append(nav_buttons)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"📖 {manga['name']} - الفصل {chapter_num}",
            reply_markup=reply_markup
        )
    
    def run(self):
        """تشغيل البوت"""
        print("🤖 البوت يعمل...")
        self.app.run_polling()

if __name__ == "__main__":
    bot = MangaBot()
    bot.run()
