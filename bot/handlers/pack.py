# bot/handlers/pack.py
"""
معالج حزم الملصقات
"""
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from ..services.pack_service import PackService
from ..utils.decorators import handle_errors, require_registration
from ..utils.helpers import sanitize_pack_name, validate_sticker_name, generate_pack_share_link
from ..utils.logger import logger
from ..keyboards.inline import InlineKeyboards
from ..database.crud import UserCRUD, PackCRUD
from ..database.database import get_db
from ..database.models import PackType

@handle_errors
@require_registration
async def create_pack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج إنشاء حزمة جديدة"""
    user_id = update.effective_user.id
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    # طلب اسم الحزمة
    messages = {
        'ar': """
📦 **إنشاء حزمة ملصقات جديدة**

الرجاء إرسال اسم الحزمة (بالأحرف الإنجليزية والأرقام):
مثال: `MyPack1`

ملاحظات:
• يجب أن يكون الاسم فريداً
• لا يمكن تغيير الاسم لاحقاً
• أضف _by_bot تلقائياً
        """,
        'en': """
📦 **Create New Sticker Pack**

Please send the pack name (English letters and numbers):
Example: `MyPack1`

Notes:
• Name must be unique
• Name cannot be changed later
• _by_bot added automatically
        """
    }
    
    context.user_data['creating_pack'] = True
    await update.message.reply_text(
        messages[language],
        parse_mode='Markdown'
    )

@handle_errors
@require_registration
async def handle_pack_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استقبال اسم الحزمة"""
    if not context.user_data.get('creating_pack'):
        return
    
    user_id = update.effective_user.id
    pack_name = update.message.text.strip()
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    # التحقق من صحة الاسم
    is_valid, result = validate_sticker_name(pack_name)
    if not is_valid:
        messages = {
            'ar': f"❌ {result}",
            'en': f"❌ {result}"
        }
        await update.message.reply_text(messages[language])
        return
    
    # حفظ اسم الحزمة مؤقتاً
    context.user_data['new_pack_name'] = pack_name
    context.user_data['creating_pack'] = False
    context.user_data['awaiting_pack_title'] = True
    
    # طلب عنوان الحزمة
    messages = {
        'ar': f"""
✅ اسم الحزمة: `{pack_name}_by_{context.bot.username}`

الآن أرسل عنوان الحزمة (اسم للقراءة، يمكن أن يكون بالعربية):
        """,
        'en': f"""
✅ Pack name: `{pack_name}_by_{context.bot.username}`

Now send the pack title (readable name):
        """
    }
    
    await update.message.reply_text(
        messages[language],
        parse_mode='Markdown'
    )

@handle_errors
@require_registration
async def handle_pack_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استقبال عنوان الحزمة"""
    if not context.user_data.get('awaiting_pack_title'):
        return
    
    user_id = update.effective_user.id
    pack_title = update.message.text.strip()
    pack_name = context.user_data.get('new_pack_name')
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    if not pack_name:
        messages = {
            'ar': "❌ حدث خطأ. الرجاء البدء من جديد باستخدام /createpack",
            'en': "❌ An error occurred. Please start again with /createpack"
        }
        await update.message.reply_text(messages[language])
        return
    
    context.user_data['new_pack_title'] = pack_title
    context.user_data['awaiting_pack_title'] = False
    
    # طلب نوع الحزمة
    messages = {
        'ar': "اختر نوع الحزمة:",
        'en': "Choose pack type:"
    }
    
    await update.message.reply_text(
        messages[language],
        reply_markup=InlineKeyboards.pack_type_selection(language)
    )

@handle_errors
@require_registration
async def my_packs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج عرض حزم المستخدم"""
    user_id = update.effective_user.id
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    # إنشاء خدمة الحزم
    pack_service = PackService(context.bot)
    packs = await pack_service.get_user_packs(user_id)
    
    if not packs:
        messages = {
            'ar': "📭 ليس لديك أي حزم ملصقات حتى الآن. أنشئ حزمة جديدة باستخدام /createpack",
            'en': "📭 You don't have any sticker packs yet. Create one with /createpack"
        }
        await update.message.reply_text(
            messages[language],
            reply_markup=InlineKeyboards.main_menu(language)
        )
        return
    
    # عرض الحزم
    if language == "ar":
        packs_text = "📦 **حزم الملصقات الخاصة بك:**\n\n"
        for pack in packs:
            packs_text += f"• **{pack['title']}** ({pack['name']})\n"
            packs_text += f"  ├ الملصقات: {pack['sticker_count']}\n"
            packs_text += f"  ├ النوع: {pack['type']}\n"
            packs_text += f"  └ [رابط المشاركة]({pack['share_link']})\n\n"
    else:
        packs_text = "📦 **Your Sticker Packs:**\n\n"
        for pack in packs:
            packs_text += f"• **{pack['title']}** ({pack['name']})\n"
            packs_text += f"  ├ Stickers: {pack['sticker_count']}\n"
            packs_text += f"  ├ Type: {pack['type']}\n"
            packs_text += f"  └ [Share Link]({pack['share_link']})\n\n"
    
    # إنشاء لوحة مفاتيح لعرض الحزم
    keyboard = []
    for pack in packs[:10]:  # عرض أول 10 حزم
        keyboard.append([
            InlineKeyboardButton(
                pack['title'],
                callback_data=f"manage_pack_{pack['name']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            "🔙 رجوع" if language == "ar" else "🔙 Back",
            callback_data="main_menu"
        )
    ])
    
    await update.message.reply_text(
        packs_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

@handle_errors
@require_registration
async def delete_pack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج حذف حزمة"""
    user_id = update.effective_user.id
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    # التحقق من وجود اسم حزمة في الأمر
    if context.args:
        pack_name = context.args[0]
        context.user_data['deleting_pack'] = pack_name
        
        messages = {
            'ar': f"⚠️ هل أنت متأكد من حذف الحزمة `{pack_name}`؟\nلا يمكن التراجع عن هذا الإجراء.",
            'en': f"⚠️ Are you sure you want to delete pack `{pack_name}`?\nThis action cannot be undone."
        }
        
        await update.message.reply_text(
            messages[language],
            reply_markup=InlineKeyboards.confirmation_keyboard("delete_pack", language),
            parse_mode='Markdown'
        )
    else:
        messages = {
            'ar': "الرجاء إرسال اسم الحزمة: /deletepack [اسم_الحزمة]",
            'en': "Please send pack name: /deletepack [pack_name]"
        }
        await update.message.reply_text(messages[language])

@handle_errors
@require_registration
async def share_pack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج مشاركة حزمة"""
    user_id = update.effective_user.id
    
    # الحصول على لغة المستخدم
    async for db in get_db():
        user_crud = UserCRUD(db)
        db_user = await user_crud.get_user(user_id)
        language = db_user.language if db_user else "ar"
    
    if context.args:
        pack_name = context.args[0]
        share_link = generate_pack_share_link(pack_name)
        
        messages = {
            'ar': f"📤 رابط مشاركة الحزمة:\n{share_link}",
            'en': f"📤 Pack share link:\n{share_link}"
        }
        
        await update.message.reply_text(messages[language])
    else:
        # عرض الحزم للاختيار
        pack_service = PackService(context.bot)
        packs = await pack_service.get_user_packs(user_id)
        
        if packs:
            keyboard = []
            for pack in packs:
                keyboard.append([
                    InlineKeyboardButton(
                        pack['title'],
                        callback_data=f"share_pack_{pack['name']}"
                    )
                ])
            
            messages = {
                'ar': "اختر الحزمة للمشاركة:",
                'en': "Choose pack to share:"
            }
            
            await update.message.reply_text(
                messages[language],
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            messages = {
                'ar': "ليس لديك أي حزم للمشاركة",
                'en': "You don't have any packs to share"
            }
            await update.message.reply_text(messages[language])

# تسجيل المعالجات
create_pack_handler = CommandHandler('createpack', create_pack_command)
my_packs_handler = CommandHandler('mypacks', my_packs_command)
delete_pack_handler = CommandHandler('deletepack', delete_pack_command)
share_pack_handler = CommandHandler('sharepack', share_pack_command)
pack_name_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pack_name)
