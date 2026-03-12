#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Бот-администратор для управления базой данных производства
Работает с Google Drive и Excel файлом
"""

import logging
import asyncio
# В самом верху bot.py добавьте:
import subprocess
import sys

print("🔍 Проверка зависимостей...")
result = subprocess.run([sys.executable, 'check_libs.py'])
if result.returncode != 0:
    print("❌ Ошибка при проверке зависимостей")
    sys.exit(1)

# Дальше идет остальной код бота
...

# Принудительно устанавливаем недостающие библиотеки
required_packages = [
    'google-auth-oauthlib==1.2.0',
    'google-auth-httplib2==0.2.0',
    'google-api-python-client==2.120.0'
]

for package in required_packages:
    try:
        __import__(package.split('==')[0].replace('-', '_'))
        print(f"✅ {package} уже установлен")
    except ImportError:
        print(f"📦 Устанавливаю {package}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.ext import ConversationHandler

from config import BOT_TOKEN, ADMIN_ID
from handlers import (
    start_command, button_handler, handle_message,
    set_excel_handler
)
from excel_handler import ExcelHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальный обработчик Excel
excel_handler = None

async def post_init(application: Application):
    """Действия после инициализации бота"""
    global excel_handler
    logger.info("🚀 Бот-администратор запускается...")
    
    # Инициализируем обработчик Excel
    excel_handler = ExcelHandler()
    set_excel_handler(excel_handler)
    
    # Проверяем авторизацию в Google Drive (но не ждём)
    if excel_handler.drive_client.creds:
        logger.info("✅ Google Drive авторизация есть")
    else:
        logger.info("🔑 Google Drive авторизация требуется при первом запуске")
    
    # Устанавливаем команды бота
    await application.bot.set_my_commands([
        ("start", "🏠 Главное меню"),
        ("cancel", "❌ Отмена текущего действия"),
        ("help", "📖 Помощь")
    ])
    
    logger.info("✅ Бот-администратор готов к работе")

def main():
    """Главная функция запуска бота"""
    # Создаём приложение
    application = Application.builder() \
        .token(BOT_TOKEN) \
        .post_init(post_init) \
        .build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик callback-запросов (кнопки)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений (для ввода данных)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("✅ Обработчики зарегистрированы")
    
    # Запускаем бота
    application.run_polling(allowed_updates=['message', 'callback_query'])

async def cancel_command(update, context):
    """Отмена текущего действия"""
    from handlers import clear_user_data
    from states import AdminStates, set_user_state
    from keyboards import main_menu_keyboard
    
    user_id = update.effective_user.id
    clear_user_data(context, user_id)
    set_user_state(context, user_id, AdminStates.MAIN_MENU)
    
    await update.message.reply_text(
        "🏭 *ГЛАВНОЕ МЕНЮ*\n\nДействие отменено. Выберите раздел:",
        reply_markup=main_menu_keyboard(user_id),
        parse_mode='Markdown'
    )

async def help_command(update, context):
    """Помощь по командам"""
    help_text = """
📖 *ПОМОЩЬ ПО БОТУ-АДМИНИСТРАТОРУ*

*Основные команды:*
/start - Главное меню
/cancel - Отмена текущего действия

*Разделы:*
📋 Категории - управление категориями
🏗️ Изделия - управление изделиями
🔩 Узлы - управление узлами
⚙️ Материалы - управление материалами

*При работе со списками:*
◀️ ▶️ - навигация по страницам
➕ Добавить - создание нового элемента
✏️ Редактировать - изменение существующего
🔗 Привязать - связывание элементов

*Важно:* 
- Данные сохраняются в Excel файл на Google Drive
- Основной бот подхватит изменения через 5 минут
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update, context):
    """Обработчик ошибок"""
    logger.error(f"❌ Ошибка: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла внутренняя ошибка. Попробуйте позже или используйте /cancel"
            )
    except:
        pass

if __name__ == '__main__':
    main()
