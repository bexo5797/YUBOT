# bot/keyboards/inline.py
"""
لوحات المفاتيح المضمنة (Inline Keyboards)
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Optional, Dict, Any

class InlineKeyboards:
    """مصنع لوحات المفاتيح المضمنة"""
    
    @staticmethod
    def main_menu(language: str = "ar") -> InlineKeyboardMarkup:
        """القائمة الرئيسية"""
        if language == "ar":
            keyboard = [
                [
                    InlineKeyboardButton("🖼 تحويل صورة لملصق", callback_data="convert_photo"),
                    InlineKeyboardButton("🎥 تحويل فيديو لملصق", callback_data="convert_video")
                ],
                [
                    InlineKeyboardButton("📦 حزم الملصقات", callback_data="my_packs"),
                    InlineKeyboardButton("➕ إنشاء حزمة جديدة", callback_data="create_pack")
                ],
                [
                    InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"),
                    InlineKeyboardButton("📊 إحصائياتي", callback_data="statistics")
                ],
                [
                    InlineKeyboardButton("❓ مساعدة", callback_data="help"),
                    InlineKeyboardButton("ℹ️ عن البوت", callback_data="about")
                ]
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("🖼 Photo to Sticker", callback_data="convert_photo"),
                    InlineKeyboardButton("🎥 Video to Sticker", callback_data="convert_video")
                ],
                [
                    InlineKeyboardButton("📦 My Packs", callback_data="my_packs"),
                    InlineKeyboardButton("➕ Create New Pack", callback_data="create_pack")
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                    InlineKeyboardButton("📊 Statistics", callback_data="statistics")
                ],
                [
                    InlineKeyboardButton("❓ Help", callback_data="help"),
                    InlineKeyboardButton("ℹ️ About", callback_data="about")
                ]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def language_selection() -> InlineKeyboardMarkup:
        """اختيار اللغة"""
        keyboard = [
            [
                InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pack_management(pack_name: str, language: str = "ar") -> InlineKeyboardMarkup:
        """إدارة الحزمة"""
        if language == "ar":
            keyboard = [
                [
                    InlineKeyboardButton("➕ إضافة ملصق", callback_data=f"add_sticker_{pack_name}"),
                    InlineKeyboardButton("👀 عرض الملصقات", callback_data=f"view_stickers_{pack_name}")
                ],
                [
                    InlineKeyboardButton("📝 تعديل الاسم", callback_data=f"rename_pack_{pack_name}"),
                    InlineKeyboardButton("🗑 حذف الحزمة", callback_data=f"delete_pack_{pack_name}")
                ],
                [
                    InlineKeyboardButton("📤 مشاركة", callback_data=f"share_pack_{pack_name}"),
                    InlineKeyboardButton("🔙 رجوع", callback_data="my_packs")
                ]
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("➕ Add Sticker", callback_data=f"add_sticker_{pack_name}"),
                    InlineKeyboardButton("👀 View Stickers", callback_data=f"view_stickers_{pack_name}")
                ],
                [
                    InlineKeyboardButton("📝 Rename", callback_data=f"rename_pack_{pack_name}"),
                    InlineKeyboardButton("🗑 Delete", callback_data=f"delete_pack_{pack_name}")
                ],
                [
                    InlineKeyboardButton("📤 Share", callback_data=f"share_pack_{pack_name}"),
                    InlineKeyboardButton("🔙 Back", callback_data="my_packs")
                ]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu(language: str = "ar") -> InlineKeyboardMarkup:
        """قائمة الإعدادات"""
        if language == "ar":
            keyboard = [
                [
                    InlineKeyboardButton("🌐 تغيير اللغة", callback_data="change_language"),
                ],
                [
                    InlineKeyboardButton("🔔 الإشعارات", callback_data="toggle_notifications"),
                ],
                [
                    InlineKeyboardButton("📊 إحصائياتي", callback_data="statistics"),
                ],
                [
                    InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="main_menu")
                ]
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("🌐 Change Language", callback_data="change_language"),
                ],
                [
                    InlineKeyboardButton("🔔 Notifications", callback_data="toggle_notifications"),
                ],
                [
                    InlineKeyboardButton("📊 Statistics", callback_data="statistics"),
                ],
                [
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")
                ]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pack_type_selection(language: str = "ar") -> InlineKeyboardMarkup:
        """اختيار نوع الحزمة"""
        if language == "ar":
            keyboard = [
                [
                    InlineKeyboardButton("🖼 ملصقات عادية", callback_data="pack_type_static"),
                ],
                [
                    InlineKeyboardButton("🎥 ملصقات متحركة", callback_data="pack_type_animated"),
                ],
                [
                    InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
                ]
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("🖼 Static Stickers", callback_data="pack_type_static"),
                ],
                [
                    InlineKeyboardButton("🎥 Animated Stickers", callback_data="pack_type_animated"),
                ],
                [
                    InlineKeyboardButton("🔙 Back", callback_data="main_menu")
                ]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirmation_keyboard(action: str, language: str = "ar") -> InlineKeyboardMarkup:
        """لوحة تأكيد الإجراء"""
        if language == "ar":
            keyboard = [
                [
                    InlineKeyboardButton("✅ نعم", callback_data=f"confirm_{action}"),
                    InlineKeyboardButton("❌ لا", callback_data=f"cancel_{action}")
                ]
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{action}"),
                    InlineKeyboardButton("❌ No", callback_data=f"cancel_{action}")
                ]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pagination_keyboard(
        current_page: int,
        total_pages: int,
        prefix: str,
        language: str = "ar"
    ) -> InlineKeyboardMarkup:
        """لوحة التصفح بين الصفحات"""
        keyboard = []
        row = []
        
        if language == "ar":
            prev_text = "⬅️ السابق"
            next_text = "التالي ➡️"
            page_text = f"📄 {current_page}/{total_pages}"
        else:
            prev_text = "⬅️ Previous"
            next_text = "Next ➡️"
            page_text = f"📄 {current_page}/{total_pages}"
        
        if current_page > 1:
            row.append(InlineKeyboardButton(
                prev_text,
                callback_data=f"{prefix}_page_{current_page-1}"
            ))
        
        row.append(InlineKeyboardButton(page_text, callback_data="ignore"))
        
        if current_page < total_pages:
            row.append(InlineKeyboardButton(
                next_text,
                callback_data=f"{prefix}_page_{current_page+1}"
            ))
        
        keyboard.append(row)
        
        if language == "ar":
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def emoji_selection(language: str = "ar") -> InlineKeyboardMarkup:
        """اختيار الإيموجي السريع"""
        emojis = ["😀", "😂", "❤️", "👍", "🔥", "😍", "🎉", "💯", "😊", "🤣"]
        
        keyboard = []
        row = []
        for i, emoji_char in enumerate(emojis):
            row.append(InlineKeyboardButton(
                emoji_char,
                callback_data=f"emoji_{emoji_char}"
            ))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        if language == "ar":
            keyboard.append([InlineKeyboardButton("🔙 تخطي", callback_data="skip_emoji")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 Skip", callback_data="skip_emoji")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_menu(language: str = "ar") -> InlineKeyboardMarkup:
        """قائمة المشرف"""
        keyboard = [
            [
                InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"),
                InlineKeyboardButton("📦 الحزم", callback_data="admin_packs")
            ],
            [
                InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats"),
                InlineKeyboardButton("📨 بث", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
