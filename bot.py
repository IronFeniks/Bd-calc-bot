#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import BOT_TOKEN, ADMIN_IDS, DATA_DIR, EXCEL_FILE
from handlers import (
    start_command, button_handler, handle_message,
    set_excel_handler
)
from excel_handler import ExcelHandler

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', mode='a', encoding='utf-8')
    ]
)

logging.getLogger('httpx').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info("🚀 Запуск бота-администратора...")
logger.info(f"Admin IDs: {ADMIN_IDS}")
logger.info(f"Excel файл: {EXCEL_FILE}")

# =========================================================================

excel_handler = None

async def post_init(application: Application):
    """Действия после инициализации бота"""
    global excel_handler
    logger.info("⚙️ Выполняется post_init...")
    
    try:
        excel_handler = ExcelHandler()
        set_excel_handler(excel_handler)
        logger.info("✅ Обработчик Excel инициализирован")
        
        # Проверяем наличие файла
        if os.path.exists(EXCEL_FILE):
            logger.info(f"✅ Файл {EXCEL_FILE} найден")
        else:
            logger.warning(f"⚠️ Файл {EXCEL_FILE} не найден")
        
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
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("✅ Все обработчики добавлены")
        
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
🔗 Привязать - связывание элементов

💾 Все изменения сохраняются в файл:
data/База для приложения.xlsx
    """
    
    await update.message.reply_text(help_text)

if __name__ == '__main__':
    main()
