import logging
import sys

# Базовая настройка логирования сразу в stderr
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger(__name__)
logger.info("🚨 ЛОГГЕР РАБОТАЕТ!")

print("🚨 PRINT РАБОТАЕТ!", flush=True)
sys.stderr.write("🚨 STDERR РАБОТАЕТ!\n")
sys.stderr.flush()

try:
    from telegram.ext import Application
    logger.info("✅ telegram.ext импортирован")
except Exception as e:
    logger.error(f"❌ Ошибка импорта telegram: {e}")

logger.info("✅ Скрипт завершён")
