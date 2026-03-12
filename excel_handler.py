import pandas as pd
import os
import logging
from config import EXCEL_FILE, DATA_DIR

logger = logging.getLogger(__name__)

class ExcelHandler:
    """Класс для работы с локальным Excel файлом"""
    
    def __init__(self):
        self.df_nomenclature = None
        self.df_specifications = None
        self.is_loaded = False
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создаёт папку data, если её нет"""
        os.makedirs(DATA_DIR, exist_ok=True)
        logger.info(f"✅ Папка {DATA_DIR} готова")
    
    def load_data(self):
        """Загружает данные из локального Excel файла"""
        try:
            if not os.path.exists(EXCEL_FILE):
                return False, f"❌ Файл {EXCEL_FILE} не найден"
            
            excel_file = pd.ExcelFile(EXCEL_FILE)
            self.df_nomenclature = pd.read_excel(excel_file, sheet_name='Номенклатура')
            self.df_specifications = pd.read_excel(excel_file, sheet_name='Спецификации')
            
            self.is_loaded = True
            logger.info(f"✅ Загружено: номенклатура {len(self.df_nomenclature)} записей")
            logger.info(f"✅ Загружено: спецификации {len(self.df_specifications)} записей")
            return True, "✅ Данные загружены"
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки: {e}")
            return False, f"❌ Ошибка: {e}"
    
    def save_data(self):
        """Сохраняет изменения обратно в файл"""
        if not self.is_loaded:
            return False, "❌ Нет загруженных данных"
        
        try:
            with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
                self.df_nomenclature.to_excel(writer, sheet_name='Номенклатура', index=False)
                self.df_specifications.to_excel(writer, sheet_name='Спецификации', index=False)
            
            logger.info("✅ Данные сохранены")
            return True, "✅ Данные сохранены"
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения: {e}")
            return False, f"❌ Ошибка: {e}"
    
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
                'name': row['Наименование']
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
        
        if code in self.df_nomenclature['Код'].values:
            return False, f"❌ Код {code} уже существует"
        
        new_row = {
            'Код': code,
            'Наименование': name,
            'Тип': type_name,
            'Цена производства': price,
            'Категории': category,
            'Кратность': multiplicity
        }
        
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
        
        mask = (self.df_specifications['Родитель'] == product_code) & \
               (self.df_specifications['Потомок'] == node_code)
        
        if len(self.df_specifications[mask]) > 0:
            return False, "❌ Такая связь уже существует"
        
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
    
    def get_product_children(self, parent_code):
        """Возвращает список всех потомков для родителя"""
        if not self.is_loaded:
            return []
        
        specs = self.df_specifications[self.df_specifications['Родитель'] == parent_code]
        result = []
        
        for _, spec in specs.iterrows():
            child_code = spec['Потомок']
            quantity = spec['Количество']
            
            child = self.get_product_by_code(child_code)
            if child:
                result.append({
                    'code': child_code,
                    'name': child['Наименование'],
                    'type': child['Тип'],
                    'quantity': quantity
                })
        
        return result
