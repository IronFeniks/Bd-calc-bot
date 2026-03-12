import sys
import time

print("🚨 ТЕСТОВЫЙ СКРИПТ ЗАПУЩЕН", flush=True)
sys.stderr.write("🚨 ТЕСТОВЫЙ СКРИПТ (stderr)\n")
sys.stderr.flush()
time.sleep(2)

print("✅ Тест завершён", flush=True)
