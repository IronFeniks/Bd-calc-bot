import pandas as pd
import os
import tempfile
import logging
from drive_client import GoogleDriveClient
from config import FILE_ID

logger = logging.getLogger(__name__)

class ExcelHandler:
    """Класс для работы с Excel файлом"""
    
    def __init__(self):
        self.drive_client = GoogleDriveClient()
        self.file_id = FILE_ID
        self.df_nomenclature = None
        self.df_specifications = None
        self.is_loaded = False
    
    def download_and_load(self):
        """Скачивает файл и загружает данные в pandas"""
        success, file_data, message = self.drive_client.download_file(self.file_id)
        if not success:
            return False, message
        
        try:
            # Читаем Excel
            excel_file = pd.ExcelFile(file_data)
            
            # Загружаем листы
            self.df_nomenclature = pd.read_excel(excel_file, sheet_name='Номенклатура')
            self.df_specifications = pd.read_excel(excel_file, sheet_name='Спецификации')
            
            self.is_loaded = True
            logger.info(f"✅ Загружено: номенклатура {len(self.df_nomenclature)} записей")
            logger.info(f"✅ Загружено: спецификации {len(self.df_specifications)} записей")
            return True, "✅ Данные загружены"
        except Exception as e:
            logger.error(f"❌ Ошибка чтения Excel: {e}")
            return False, f"❌ Ошибка чтения файла: {e}"
    
    def save_and_upload(self):
        """Сохраняет DataFrame обратно в Excel и загружает на Диск"""
        if not self.is_loaded:
            return False, "❌ Нет загруженных данных"
        
        temp_path = None
        try:
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                temp_path = tmp.name
            
            # Сохраняем в Excel
            with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
                self.df_nomenclature.to_excel(writer, sheet_name='Номенклатура', index=False)
                self.df_specifications.to_excel(writer, sheet_name='Спецификации', index=False)
            
            logger.info(f"✅ Excel сохранён временно: {temp_path}")
            
            # Загружаем на Диск
            success, message = self.drive_client.upload_file(self.file_id, temp_path)
            
            return success, message
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения Excel: {e}")
            return False, f"❌ Ошибка сохранения: {e}"
        finally:
            # Удаляем временный файл
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def get_unique_categories(self):
        """Возвращает список уникальных категорий"""
        if not self.is_loaded:
            return []
        
        categories = self.df_nomenclature['Категории'].dropna().unique().tolist()
        return sorted([str(c) for c in categories if str(c).strip()])
    
    def get_products_by_category(self, category, page=0, items_per_page=10):
        """Возвращает список изделий в категории с пагинацией"""
        if not self.is_loaded:
            return [], 0
        
        mask = (self.df_nomenclature['Категории'] == category) & \
               (self.df_nomenclature['Тип'].str.lower().isin(['изделие', 'узел']))
        
        filtered = self.df_nomenclature[mask]
        total = len(filtered)
        
        start = page * items_per_page
        end = min(start + items_per_page, total)
        
        result = []
        for idx, row in filtered.iloc[start:end].iterrows():
            result.append({
                'code': row['Код'],
                'name': row['Наименование'],
                'type': row['Тип'],
                'price': row.get('Цена производства', '0 ISK'),
                'multiplicity': row.get('Кратность', 1)
            })
        
        return result, total
    
    def get_materials(self, page=0, items_per_page=10):
        """Возвращает список материалов с пагинацией"""
        if not self.is_loaded:
            return [], 0
        
        mask = self.df_nomenclature['Тип'].str.lower() == 'материал'
        filtered = self.df_nomenclature[mask]
        total = len(filtered)
        
        start = page * items_per_page
        end = min(start + items_per_page, total)
        
        result = []
        for idx, row in filtered.iloc[start:end].iterrows():
            result.append({
                'code': row['Код'],
                'name': row['Наименование']
            })
        
        return result, total
    
    def get_product_by_code(self, code):
        """Возвращает изделие/узел по коду"""
        if not self.is_loaded:
            return None
        
        row = self.df_nomenclature[self.df_nomenclature['Код'] == code]
        if len(row) == 0:
            return None
        
        return row.iloc[0].to_dict()
    
    def add_product(self, code, name, type_name, category, price='0 ISK', multiplicity=1):
        """Добавляет новое изделие/узел"""
        if not self.is_loaded:
            return False, "❌ Данные не загружены"
        
        # Проверяем уникальность кода
        if code in self.df_nomenclature['Код'].values:
            return False, f"❌ Код {code} уже существует"
        
        # Создаём новую строку
        new_row = {
            'Код': code,
            'Наименование': name,
            'Тип': type_name,
            'Цена производства': price,
            'Категории': category,
            'Кратность': multiplicity
        }
        
        # Добавляем строку
        self.df_nomenclature = pd.concat([self.df_nomenclature, pd.DataFrame([new_row])], ignore_index=True)
        
        return True, f"✅ {type_name} '{name}' успешно добавлен"
    
    def add_material(self, code, name, category=''):
        """Добавляет новый материал"""
        if not self.is_loaded:
            return False, "❌ Данные не загружены"
        
        if code in self.df_nomenclature['Код'].values:
            return False, f"❌ Код {code} уже существует"
        
        new_row = {
            'Код': code,
            'Наименование': name,
            'Тип': 'материал',
            'Цена производства': '',
            'Категории': category,
            'Кратность': ''
        }
        
        self.df_nomenclature = pd.concat([self.df_nomenclature, pd.DataFrame([new_row])], ignore_index=True)
        
        return True, f"✅ Материал '{name}' успешно добавлен"
    
    def link_node_to_product(self, product_code, node_code, quantity):
        """Привязывает узел к изделию"""
        if not self.is_loaded:
            return False, "❌ Данные не загружены"
        
        # Проверяем, существует ли уже такая связь
        mask = (self.df_specifications['Родитель'] == product_code) & \
               (self.df_specifications['Потомок'] == node_code)
        
        if len(self.df_specifications[mask]) > 0:
            return False, "❌ Такая связь уже существует"
        
        # Добавляем новую связь
        new_row = {
            'Родитель': product_code,
            'Потомок': node_code,
            'Количество': quantity
        }
        
        self.df_specifications = pd.concat([self.df_specifications, pd.DataFrame([new_row])], ignore_index=True)
        
        return True, f"✅ Узел привязан с количеством {quantity}"
    
    def link_material_to_product(self, parent_code, material_code, quantity):
        """Привязывает материал к изделию или узлу"""
        if not self.is_loaded:
            return False, "❌ Данные не загружены"
        
        mask = (self.df_specifications['Родитель'] == parent_code) & \
               (self.df_specifications['Потомок'] == material_code)
        
        if len(self.df_specifications[mask]) > 0:
            return False, "❌ Такая связь уже существует"
        
        new_row = {
            'Родитель': parent_code,
            'Потомок': material_code,
            'Количество': quantity
        }
        
        self.df_specifications = pd.concat([self.df_specifications, pd.DataFrame([new_row])], ignore_index=True)
        
        return True, f"✅ Материал привязан с количеством {quantity}"
