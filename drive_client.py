import os
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, TOKEN_FILE

logger = logging.getLogger(__name__)

class GoogleDriveClient:
    """Клиент для работы с Google Drive API"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.load_credentials()
    
    def load_credentials(self):
        """Загружает сохранённые учетные данные из файла"""
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                    self.creds = Credentials.from_authorized_user_info(token_data, self.SCOPES)
                    logger.info("✅ Токены загружены из файла")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки токенов: {e}")
    
    def save_credentials(self):
        """Сохраняет учетные данные в файл"""
        if self.creds:
            try:
                token_data = {
                    'token': self.creds.token,
                    'refresh_token': self.creds.refresh_token,
                    'token_uri': self.creds.token_uri,
                    'client_id': self.creds.client_id,
                    'client_secret': self.creds.client_secret,
                    'scopes': self.creds.scopes
                }
                with open(TOKEN_FILE, 'w') as f:
                    json.dump(token_data, f)
                logger.info("✅ Токены сохранены в файл")
            except Exception as e:
                logger.error(f"❌ Ошибка сохранения токенов: {e}")
    
    def get_auth_url(self):
        """Возвращает URL для авторизации и flow объект"""
        client_config = {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        }
        
        flow = InstalledAppFlow.from_client_config(
            client_config,
            self.SCOPES
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return auth_url, flow
    
    def exchange_code(self, code, flow):
        """Обменивает код подтверждения на токены"""
        try:
            flow.fetch_token(code=code)
            self.creds = flow.credentials
            self.save_credentials()
            self.service = build('drive', 'v3', credentials=self.creds)
            return True, "✅ Авторизация успешна"
        except Exception as e:
            logger.error(f"❌ Ошибка обмена кода: {e}")
            return False, f"❌ Ошибка авторизации: {e}"
    
    def ensure_auth(self):
        """Проверяет наличие действующих токенов"""
        if not self.creds:
            return False, "Требуется авторизация"
        
        if self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                self.save_credentials()
                logger.info("✅ Токены обновлены")
            except Exception as e:
                logger.error(f"❌ Ошибка обновления токенов: {e}")
                return False, "Ошибка обновления токенов"
        
        if not self.service:
            self.service = build('drive', 'v3', credentials=self.creds)
        
        return True, self.service
    
    def download_file(self, file_id):
        """Скачивает файл с Google Диска"""
        success, result = self.ensure_auth()
        if not success:
            return False, None, result
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_data = io.BytesIO()
            downloader = MediaIoBaseDownload(file_data, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                logger.info(f"📥 Скачивание: {int(status.progress() * 100)}%")
            
            file_data.seek(0)
            logger.info(f"✅ Файл скачан, размер: {len(file_data.getvalue())} байт")
            return True, file_data, "✅ Файл скачан"
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания: {e}")
            return False, None, f"❌ Ошибка: {e}"
    
    def upload_file(self, file_id, file_path, mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'):
        """Загружает файл на Google Диск"""
        success, result = self.ensure_auth()
        if not success:
            return False, result
        
        try:
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            updated_file = self.service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            logger.info(f"✅ Файл обновлён: {updated_file.get('name')}")
            return True, "✅ Файл успешно обновлён"
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки: {e}")
            return False, f"❌ Ошибка загрузки: {e}"
