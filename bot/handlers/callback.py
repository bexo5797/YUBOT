# bot/handlers/callback.py
"""
معالج أزرار الرد المضمنة (Callback Queries)
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes
from ..utils.decorators import handle_errors, require_registration
from ..utils.logger import logger
from ..utils.helpers import generate_pack_share_link
from ..keyboards.inline import InlineKeyboards
from ..keyboards.reply import ReplyKeyboards
from ..services.pack_service import PackService
from ..services.sticker_service import StickerService
from ..database.crud import UserCRUD, PackCRUD, StickerCRUD
from ..database.database import get_db
from ..database.models import PackType

@handle_errors
@require_registration
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """المعالج الرئيسي لأزرار الرد"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    # معالجة أنواع مختلفة من الردود
    if data == "main_menu":
        await show_main_menu(query, language)
    
    elif data == "convert_photo":
        await handle_convert_photo(query, language)
    
    elif data == "convert_video":
        await handle_convert_video(query, language)
    
    elif data == "my_packs":
        await handle_my_packs(query, context, user_id, language)
    
    elif data == "create_pack":
        await handle_create_pack(query, language)
    
    elif data == "settings":
        await handle_settings(query, language)
    
    elif data == "statistics":
        await handle_statistics(query, context, user_id, language)
    
    elif data == "help":
        await handle_help(query, language)
    
    elif data == "about":
        await handle_about(query, language)
    
    elif data == "change_language":
        await handle_change_language(query, language)
    
    elif data.startswith("lang_"):
        new_lang = data.split("_")[1]
        await handle_language_selection(query, user_id, new_lang)
    
    elif data.startswith("pack_type_"):
        pack_type = data.split("_")[2]
        await handle_pack_type_selection(query, context, user_id, pack_type, language)
    
    elif data.startswith("manage_pack_"):
        pack_name = data.replace("manage_pack_", "")
        await handle_manage_pack(query, pack_name, language)
    
    elif data.startswith("add_sticker_"):
        pack_name = data.replace("add_sticker_", "")
        await handle_add_sticker(query, context, pack_name, language)
    
    elif data.startswith("view_stickers_"):
        pack_name = data.replace("view_stickers_", "")
        await handle_view_stickers(query, context, pack_name, language)
    
    elif data.startswith("delete_pack_"):
        pack_name = data.replace("delete_pack_", "")
        await handle_delete_pack_confirmation(query, pack_name, language)
    
    elif data.startswith("confirm_"):
        action = data.replace("confirm_", "")
        await handle_confirmation(query, context, action, user_id, language)
    
    elif data.startswith("cancel_"):
        await handle_cancel(query, language)
    
    elif data.startswith("share_pack_"):
        pack_name = data.replace("share_pack_", "")
        await handle_share_pack(query, pack_name, language)
    
    elif data.startswith("emoji_"):
        emoji_char = data.replace("emoji_", "")
        await handle_emoji_callback(query, context, emoji_char, language)
    
    elif data == "skip_emoji":
        await handle_skip_emoji(query, context, language)
    
    elif data == "toggle_notifications":
        await handle_toggle_notifications(query, user_id, language)
    
    else:
        await query.edit_message_text(
            text="هذا الزر غير معروف" if language == "ar" else "Unknown button"
        )

async def show_main_menu(query, language: str):
    """عرض القائمة الرئيسية"""
    text = "القائمة الرئيسية:" if language == "ar" else "Main Menu:"
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.main_menu(language)
    )

async def handle_convert_photo(query, language: str):
    """معالج تحويل الصورة"""
    text = (
        "🖼 أرسل الصورة التي تريد تحويلها لملصق\n\n"
        "المتطلبات:\n"
        "• صيغة JPEG أو PNG\n"
        "• الحجم أقل من 10 ميجابايت\n"
        "• يفضل صور PNG للخلفيات الشفافة"
    ) if language == "ar" else (
        "🖼 Send the photo you want to convert to a sticker\n\n"
        "Requirements:\n"
        "• JPEG or PNG format\n"
        "• Size less than 10MB\n"
        "• PNG preferred for transparent backgrounds"
    )
    
    await query.edit_message_text(text=text)

async def handle_convert_video(query, language: str):
    """معالج تحويل الفيديو"""
    text = (
        "🎥 أرسل الفيديو الذي تريد تحويله لملصق متحرك\n\n"
        "المتطلبات:\n"
        "• صيغة MP4\n"
        "• المدة 3 ثواني كحد أقصى\n"
        "• الحجم أقل من 50 ميجابايت\n"
        "• يجب تثبيت FFmpeg"
    ) if language == "ar" else (
        "🎥 Send the video you want to convert to an animated sticker\n\n"
        "Requirements:\n"
        "• MP4 format\n"
        "• Maximum duration 3 seconds\n"
        "• Size less than 50MB\n"
        "• FFmpeg must be installed"
    )
    
    await query.edit_message_text(text=text)

async def handle_my_packs(query, context, user_id: int, language: str):
    """معالج عرض الحزم"""
    pack_service = PackService(context.bot)
    packs = await pack_service.get_user_packs(user_id)
    
    if not packs:
        text = (
            "📭 ليس لديك أي حزم ملصقات حتى الآن.\n"
            "أنشئ حزمة جديدة من القائمة الرئيسية!"
        ) if language == "ar" else (
            "📭 You don't have any sticker packs yet.\n"
            "Create a new pack from the main menu!"
        )
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboards.main_menu(language)
        )
        return
    
    text = "📦 **حزم الملصقات الخاصة بك:**\n\n" if language == "ar" else "📦 **Your Sticker Packs:**\n\n"
    
    keyboard = []
    for pack in packs[:20]:
        text += f"• {pack['title']} ({pack['sticker_count']} ملصق)\n" if language == "ar" else f"• {pack['title']} ({pack['sticker_count']} stickers)\n"
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {pack['title']}",
                callback_data=f"manage_pack_{pack['name']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            "🔙 رجوع" if language == "ar" else "🔙 Back",
            callback_data="main_menu"
        )
    ])
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_create_pack(query, language: str):
    """معالج إنشاء حزمة جديدة"""
    text = (
        "📦 **إنشاء حزمة ملصقات جديدة**\n\n"
        "أرسل اسم الحزمة باستخدام الأمر:\n"
        "`/createpack`\n\n"
        "أو اختر من القائمة أدناه"
    ) if language == "ar" else (
        "📦 **Create New Sticker Pack**\n\n"
        "Send the pack name using:\n"
        "`/createpack`\n\n"
        "Or choose from the menu below"
    )
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.main_menu(language),
        parse_mode='Markdown'
    )

async def handle_manage_pack(query, pack_name: str, language: str):
    """معالج إدارة حزمة محددة"""
    text = f"إدارة الحزمة: {pack_name}" if language == "ar" else f"Manage Pack: {pack_name}"
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.pack_management(pack_name, language)
    )

async def handle_add_sticker(query, context, pack_name: str, language: str):
    """معالج إضافة ملصق إلى حزمة"""
    context.user_data['current_pack'] = pack_name
    
    text = (
        f"➕ إضافة ملصق إلى الحزمة: {pack_name}\n\n"
        "أرسل الصورة أو الملصق الذي تريد إضافته"
    ) if language == "ar" else (
        f"➕ Add sticker to pack: {pack_name}\n\n"
        "Send the photo or sticker you want to add"
    )
    
    await query.edit_message_text(text=text)

async def handle_view_stickers(query, context, pack_name: str, language: str):
    """معالج عرض ملصقات الحزمة"""
    try:
        pack_service = PackService(context.bot)
        pack_info = await pack_service.get_pack_info(pack_name)
        
        if pack_info and pack_info.get('stickers'):
            stickers_count = len(pack_info['stickers'])
            text = (
                f"📦 حزمة: {pack_info['title']}\n"
                f"عدد الملصقات: {stickers_count}\n\n"
            ) if language == "ar" else (
                f"📦 Pack: {pack_info['title']}\n"
                f"Stickers count: {stickers_count}\n\n"
            )
            
            # إرسال الملصقات
            for sticker in pack_info['stickers'][:10]:  # أول 10 ملصقات
                try:
                    await context.bot.send_sticker(
                        chat_id=query.message.chat_id,
                        sticker=sticker['file_id']
                    )
                except:
                    pass
            
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboards.pack_management(pack_name, language)
            )
        else:
            text = "لا توجد ملصقات في هذه الحزمة" if language == "ar" else "No stickers in this pack"
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboards.pack_management(pack_name, language)
            )
            
    except Exception as e:
        logger.error(f"خطأ في عرض الملصقات: {e}")
        text = "حدث خطأ في عرض الملصقات" if language == "ar" else "Error displaying stickers"
        await query.edit_message_text(text=text)

async def handle_settings(query, language: str):
    """معالج الإعدادات"""
    text = "⚙️ **الإعدادات**" if language == "ar" else "⚙️ **Settings**"
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.settings_menu(language),
        parse_mode='Markdown'
    )

async def handle_statistics(query, context, user_id: int, language: str):
    """معالج الإحصائيات"""
    async for db in get_db():
        user_crud = UserCRUD(db)
        pack_crud = PackCRUD(db)
        
        stats = await user_crud.get_user_stats(user_id)
        packs_count = await pack_crud.get_user_packs_count(user_id)
        
        if language == "ar":
            text = f"""
📊 **إحصائياتك**

👤 المستخدم: {user_id}
📦 عدد الحزم: {packs_count}
🎯 عدد الملصقات: {stats.get('total_stickers', 0)}
🌐 اللغة: {'العربية' if stats.get('language') == 'ar' else 'English'}
📅 تاريخ التسجيل: {stats.get('created_at', 'غير معروف')}
            """
        else:
            text = f"""
📊 **Your Statistics**

👤 User: {user_id}
📦 Packs: {packs_count}
🎯 Stickers: {stats.get('total_stickers', 0)}
🌐 Language: {'Arabic' if stats.get('language') == 'ar' else 'English'}
📅 Joined: {stats.get('created_at', 'Unknown')}
            """
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboards.main_menu(language),
            parse_mode='Markdown'
        )

async def handle_help(query, language: str):
    """معالج المساعدة"""
    if language == "ar":
        text = """
❓ **المساعدة**

**الأوامر المتاحة:**
/start - بدء البوت
/createpack - إنشاء حزمة جديدة
/mypacks - عرض حزمي
/deletepack - حذف حزمة
/sharepack - مشاركة حزمة
/settings - الإعدادات
/language - تغيير اللغة
/help - المساعدة

**للحصول على مساعدة إضافية:**
يمكنك مراسلة المطور
        """
    else:
        text = """
❓ **Help**

**Available Commands:**
/start - Start bot
/createpack - Create new pack
/mypacks - View my packs
/deletepack - Delete a pack
/sharepack - Share a pack
/settings - Settings
/language - Change language
/help - Help

**For additional help:**
Contact the developer
        """
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.main_menu(language),
        parse_mode='Markdown'
    )

async def handle_about(query, language: str):
    """معالج عن البوت"""
    if language == "ar":
        text = """
ℹ️ **عن البوت**

🤖 **بوت الملصقات الاحترافي**
الإصدار: 1.0.0

مطور بواسطة فريق محترف
باستخدام Python و python-telegram-bot

المميزات:
• تحويل الصور لملصقات
• تحويل الفيديو لملصقات متحركة
• إدارة حزم الملصقات
• دعم العربية والإنجليزية
        """
    else:
        text = """
ℹ️ **About the Bot**

🤖 **Professional Sticker Bot**
Version: 1.0.0

Developed by a professional team
Using Python & python-telegram-bot

Features:
• Convert photos to stickers
• Convert videos to animated stickers
• Manage sticker packs
• Arabic and English support
        """
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.main_menu(language),
        parse_mode='Markdown'
    )

async def handle_change_language(query, language: str):
    """معالج تغيير اللغة"""
    text = "اختر اللغة:" if language == "ar" else "Choose language:"
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.language_selection()
    )

async def handle_language_selection(query, user_id: int, new_lang: str):
    """معالج اختيار اللغة"""
    async for db in get_db():
        user_crud = UserCRUD(db)
        await user_crud.update_language(user_id, new_lang)
    
    if new_lang == "ar":
        text = "✅ تم تغيير اللغة إلى العربية"
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboards.main_menu("ar")
        )
    else:
        text = "✅ Language changed to English"
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboards.main_menu("en")
        )

async def handle_pack_type_selection(query, context, user_id: int, pack_type: str, language: str):
    """معالج اختيار نوع الحزمة"""
    pack_name = context.user_data.get('new_pack_name')
    pack_title = context.user_data.get('new_pack_title')
    
    if not pack_name or not pack_title:
        text = "حدث خطأ، ابدأ من جديد" if language == "ar" else "Error, start over"
        await query.edit_message_text(text=text)
        return
    
    if pack_type == "static":
        type_enum = PackType.STATIC
        type_text = "عادية" if language == "ar" else "Static"
    else:
        type_enum = PackType.ANIMATED
        type_text = "متحركة" if language == "ar" else "Animated"
    
    # إنشاء الحزمة
    pack_service = PackService(context.bot)
    full_name = f"{pack_name}_by_{context.bot.username}"
    
    success, message, share_link = await pack_service.create_pack(
        user_id=user_id,
        pack_name=pack_name,
        pack_title=pack_title,
        pack_type=type_enum
    )
    
    if success:
        if language == "ar":
            text = f"""
✅ **تم إنشاء الحزمة بنجاح!**

📦 الاسم: `{full_name}`
📝 العنوان: {pack_title}
🏷 النوع: {type_text}
🔗 [رابط المشاركة]({share_link})

يمكنك الآن إضافة ملصقات إلى حزمتك!
            """
        else:
            text = f"""
✅ **Pack Created Successfully!**

📦 Name: `{full_name}`
📝 Title: {pack_title}
🏷 Type: {type_text}
🔗 [Share Link]({share_link})

You can now add stickers to your pack!
            """
    else:
        text = f"❌ {message}"
    
    # تنظيف البيانات المؤقتة
    context.user_data.pop('new_pack_name', None)
    context.user_data.pop('new_pack_title', None)
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.main_menu(language),
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

async def handle_delete_pack_confirmation(query, pack_name: str, language: str):
    """معالج تأكيد حذف الحزمة"""
    text = (
        f"⚠️ هل أنت متأكد من حذف الحزمة `{pack_name}`؟\n"
        "لا يمكن التراجع عن هذا الإجراء!"
    ) if language == "ar" else (
        f"⚠️ Are you sure you want to delete pack `{pack_name}`?\n"
        "This action cannot be undone!"
    )
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.confirmation_keyboard(f"delete_{pack_name}", language),
        parse_mode='Markdown'
    )

async def handle_confirmation(query, context, action: str, user_id: int, language: str):
    """معالج تأكيد الإجراءات"""
    if action.startswith("delete_pack_"):
        pack_name = action.replace("delete_pack_", "")
        pack_service = PackService(context.bot)
        
        success, message = await pack_service.delete_pack(user_id, pack_name)
        
        if success:
            text = "✅ تم حذف الحزمة بنجاح" if language == "ar" else "✅ Pack deleted successfully"
        else:
            text = f"❌ {message}"
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboards.main_menu(language)
        )
    
    elif action == "delete_pack":
        # حذف من خلال الأمر
        pack_name = context.user_data.get('deleting_pack')
        if pack_name:
            pack_service = PackService(context.bot)
            success, message = await pack_service.delete_pack(user_id, pack_name)
            
            if success:
                text = "✅ تم حذف الحزمة بنجاح" if language == "ar" else "✅ Pack deleted successfully"
            else:
                text = f"❌ {message}"
            
            context.user_data.pop('deleting_pack', None)
            
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboards.main_menu(language)
            )

async def handle_cancel(query, language: str):
    """معالج إلغاء الإجراءات"""
    text = "تم الإلغاء" if language == "ar" else "Cancelled"
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.main_menu(language)
    )

async def handle_share_pack(query, pack_name: str, language: str):
    """معالج مشاركة الحزمة"""
    share_link = generate_pack_share_link(pack_name)
    
    text = (
        f"📤 **مشاركة الحزمة**\n\n"
        f"رابط المشاركة:\n"
        f"[{share_link}]({share_link})\n\n"
        f"يمكن لأي شخص إضافة هذه الحزمة باستخدام الرابط!"
    ) if language == "ar" else (
        f"📤 **Share Pack**\n\n"
        f"Share link:\n"
        f"[{share_link}]({share_link})\n\n"
        f"Anyone can add this pack using the link!"
    )
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.main_menu(language),
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

async def handle_emoji_callback(query, context, emoji_char: str, language: str):
    """معالج اختيار الإيموجي من الأزرار"""
    context.user_data['last_emoji'] = emoji_char
    context.user_data['awaiting_emoji'] = False
    
    text = f"✅ تم اختيار الإيموجي: {emoji_char}" if language == "ar" else f"✅ Emoji selected: {emoji_char}"
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.main_menu(language)
    )

async def handle_skip_emoji(query, context, language: str):
    """معالج تخطي الإيموجي"""
    context.user_data['awaiting_emoji'] = False
    
    text = "تم التخطي" if language == "ar" else "Skipped"
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.main_menu(language)
    )

async def handle_toggle_notifications(query, user_id: int, language: str):
    """معالج تفعيل/تعطيل الإشعارات"""
    async for db in get_db():
        user_crud = UserCRUD(db)
        user = await user_crud.get_user(user_id)
        
        if user:
            new_status = not user.notifications_enabled
            user.notifications_enabled = new_status
            await db.commit()
            
            if language == "ar":
                status_text = "مفعلة" if new_status else "معطلة"
                text = f"🔔 الإشعارات الآن {status_text}"
            else:
                status_text = "enabled" if new_status else "disabled"
                text = f"🔔 Notifications now {status_text}"
        else:
            text = "حدث خطأ" if language == "ar" else "An error occurred"
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.settings_menu(language)
    )

# تسجيل المعالج
callback_query_handler = CallbackQueryHandler(callback_handler)
