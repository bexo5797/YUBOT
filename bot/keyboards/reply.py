# bot/keyboards/reply.py
"""
لوحات المفاتيح العادية (Reply Keyboards)
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton
from typing import List, Optional

class ReplyKeyboards:
    """مصنع لوحات المفاتيح العادية"""
    
    @staticmethod
    def main_keyboard(language: str = "ar") -> ReplyKeyboardMarkup:
        """لوحة المفاتيح الرئيسية"""
        if language == "ar":
            keyboard = [
                ["🖼 صورة لملصق", "🎥 فيديو لملصق"],
                ["📦 حزمي", "⚙️ إعدادات"],
                ["❓ مساعدة"]
            ]
        else:
            keyboard = [
                ["🖼 Photo to Sticker", "🎥 Video to Sticker"],
                ["📦 My Packs", "⚙️ Settings"],
                ["❓ Help"]
            ]
        
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            persistent=True
        )
    
    @staticmethod
    def cancel_keyboard(language: str = "ar") -> ReplyKeyboardMarkup:
        """لوحة إلغاء الأمر"""
        text = "❌ إلغاء" if language == "ar" else "❌ Cancel"
        keyboard = [[text]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def phone_keyboard(language: str = "ar") -> ReplyKeyboardMarkup:
        """طلب رقم الهاتف"""
        text = "📱 مشاركة رقم الهاتف" if language == "ar" else "📱 Share Phone Number"
        keyboard = [[KeyboardButton(text, request_contact=True)]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
