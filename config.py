import os

# ==================== НАСТРОЙКИ БОТА ====================
# Эти переменные будут браться из настроек хостинга (Bothost)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

# ==================== НАСТРОЙКИ GOOGLE DRIVE ====================
FILE_ID = os.environ.get('FILE_ID', '')
CLIENT_ID = os.environ.get('CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET', '')

# Redirect URI для Desktop приложения
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

# Путь к файлу с токенами
TOKEN_FILE = "token.json"

# ==================== НАСТРОЙКИ ПАГИНАЦИИ ====================
ITEMS_PER_PAGE = 10
