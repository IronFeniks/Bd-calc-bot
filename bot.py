#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import __version__ as TG_VER

from config import BOT_TOKEN, ADMIN_ID
from handlers import (
    start_command, button_handler, handle_message,
    set_excel_handler
)
from excel_handler import ExcelHandler

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler('bot_debug.log', mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info("🚀 Запуск бота-администратора...")
logger.info(f"Python version: {sys.version}")
logger.info(f"python-telegram-bot version: {TG_VER}")
logger.info(f"Admin ID: {ADMIN_ID}")
logger.info(f"Bot Token starts with: {BOT_TOKEN[:5]}..." if BOT_TOKEN else "❌ Токен не найден!")

# =========================================================================

excel_handler = None

async def post_init(application: Application):
    global excel_handler
    logger.info("⚙️ Выполняется post_init...")
    
    try:
        excel_handler = ExcelHandler()
        set_excel_handler(excel_handler)
        logger.info("✅ Обработчик Excel инициализирован")
        
        if excel_handler.drive_client.creds:
            logger.info("✅ Google Drive авторизация есть")
        else:
            logger.info("🔑 Google Drive авторизация требуется при первом запуске")
        
        await application.bot.set_my_commands([
            ("start", "🏠 Главное меню"),
            ("cancel", "❌ Отмена текущего действия"),
            ("help", "📖 Помощь")
        ])
        logger.info("✅ Команды бота установлены")
        
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка в post_init: {e}")

def main():
    logger.info("=" * 50)
    logger.info("⚙️ ЗАПУСК MAIN ФУНКЦИИ")
    logger.info("=" * 50)
    
    try:
        if not BOT_TOKEN:
            logger.critical("❌ BOT_TOKEN не найден!")
            return
        
        logger.info("🔄 Создание приложения...")
        application = Application.builder() \
            .token(BOT_TOKEN) \
            .post_init(post_init) \
            .build()
        logger.info("✅ Приложение создано")
        
        logger.info("🔄 Добавление обработчиков...")
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(CommandHandler("help", help_command))
        logger.info("✅ Команды добавлены")
        
        application.add_handler(CallbackQueryHandler(button_handler))
        logger.info("✅ Callback обработчик добавлен")
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("✅ Message обработчик добавлен")
        
        application.add_error_handler(error_handler)
        logger.info("✅ Error обработчик добавлен")
        
        logger.info("🎉 Все обработчики зарегистрированы")
        logger.info("🔄 Запуск polling...")
        
        application.run_polling(allowed_updates=['message', 'callback_query'])
        
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка в main: {e}")
        raise

async def cancel_command(update, context):
    from handlers import clear_user_data
    from states import AdminStates, set_user_state
    from keyboards import main_menu_keyboard
    
    user_id = update.effective_user.id
    logger.info(f"🛑 Команда /cancel от пользователя {user_id}")
    clear_user_data(context, user_id)
    set_user_state(context, user_id, AdminStates.MAIN_MENU)
    
    await update.message.reply_text(
        "🏭 ГЛАВНОЕ МЕНЮ\n\nДействие отменено. Выберите раздел:",
        reply_markup=main_menu_keyboard(user_id)
    )

async def help_command(update, context):
    user_id = update.effective_user.id
    logger.info(f"📖 Команда /help от пользователя {user_id}")
    
    help_text = """
📖 ПОМОЩЬ ПО БОТУ-АДМИНИСТРАТОРУ

Основные команды:
/start - Главное меню
/cancel - Отмена текущего действия

Разделы:
📋 Категории - управление категориями
🏗️ Изделия - управление изделиями
🔩 Узлы - управление узлами
⚙️ Материалы - управление материалами

При работе со списками:
◀️ ▶️ - навигация по страницам
➕ Добавить - создание нового элемента
✏️ Редактировать - изменение существующего
🔗 Привязать - связывание элементов

Важно: 
- Данные сохраняются в Excel файл на Google Drive
- Основной бот подхватит изменения через 5 минут
    """
    
    await update.message.reply_text(help_text)

async def error_handler(update, context):
    logger.error(f"❌ Ошибка: {context.error}", exc_info=True)
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла внутренняя ошибка. Администратор уже уведомлен."
            )
    except Exception as e:
        logger.error(f"❌ Не удалось отправить сообщение об ошибке: {e}")

if __name__ == '__main__':
    main()
