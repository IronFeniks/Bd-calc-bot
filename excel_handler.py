import pandas as pd
import os
import logging
from typing import Tuple, List, Dict, Optional
import re

logger = logging.getLogger(__name__)

class ExcelHandler:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df_nomenclature = None
        self.df_specifications = None
        self.load_data()
    
    def load_data(self) -> Tuple[bool, str]:
        """Загружает данные из Excel файла"""
        try:
            if not os.path.exists(self.file_path):
                return False, f"❌ Файл не найден: {self.file_path}"
            
            # Читаем все листы
            excel_file = pd.ExcelFile(self.file_path)
            
            if 'Номенклатура' not in excel_file.sheet_names:
                return False, "❌ В файле нет листа 'Номенклатура'"
            
            if 'Спецификации' not in excel_file.sheet_names:
                return False, "❌ В файле нет листа 'Спецификации'"
            
            self.df_nomenclature = pd.read_excel(excel_file, sheet_name='Номенклатура')
            self.df_specifications = pd.read_excel(excel_file, sheet_name='Спецификации')
            
            # Заполняем NaN пустыми строками
            self.df_nomenclature = self.df_nomenclature.fillna('')
            self.df_specifications = self.df_specifications.fillna('')
            
            logger.info(f"✅ Загружено: {len(self.df_nomenclature)} записей номенклатуры, {len(self.df_specifications)} спецификаций")
            return True, "✅ Данные загружены"
            
        except Exception as e:
            logger.error(f"Ошибка загрузки Excel: {e}")
            return False, f"❌ Ошибка загрузки: {e}"
    
    def save_data(self) -> Tuple[bool, str]:
        """Сохраняет данные в Excel файл"""
        try:
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                self.df_nomenclature.to_excel(writer, sheet_name='Номенклатура', index=False)
                self.df_specifications.to_excel(writer, sheet_name='Спецификации', index=False)
            
            logger.info("✅ Данные сохранены в Excel")
            return True, "✅ Данные сохранены"
            
        except Exception as e:
            logger.error(f"Ошибка сохранения Excel: {e}")
            return False, f"❌ Ошибка сохранения: {e}"
    
    # ==================== УПРАВЛЕНИЕ КАТЕГОРИЯМИ ====================
    
    def get_unique_categories(self) -> List[str]:
        """Возвращает список уникальных категорий"""
        categories = set()
        
        # Собираем категории из номенклатуры
        for cat in self.df_nomenclature['Категории']:
            if cat and str(cat).strip():
                parts = str(cat).split(' > ')
                for part in parts:
                    if part.strip():
                        categories.add(part.strip())
        
        # Добавляем категории из отдельного файла
        try:
            categories_file = os.path.join('data', 'categories.txt')
            if os.path.exists(categories_file):
                with open(categories_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        cat = line.strip()
                        if cat:
                            categories.add(cat)
        except Exception as e:
            logger.error(f"Ошибка чтения файла категорий: {e}")
        
        return sorted(list(categories))
    
    def add_category(self, category_name: str) -> Tuple[bool, str]:
        """Добавляет новую категорию"""
        try:
            categories_file = os.path.join('data', 'categories.txt')
            os.makedirs('data', exist_ok=True)
            
            # Проверяем, не существует ли уже
            existing = self.get_unique_categories()
            if category_name in existing:
                return False, f"❌ Категория '{category_name}' уже существует"
            
            with open(categories_file, 'a', encoding='utf-8') as f:
                f.write(f"{category_name}\n")
            
            logger.info(f"✅ Категория '{category_name}' добавлена")
            return True, f"✅ Категория '{category_name}' добавлена"
            
        except Exception as e:
            logger.error(f"Ошибка добавления категории: {e}")
            return False, f"❌ Ошибка: {e}"
    
    # ==================== АВТОМАТИЧЕСКАЯ ГЕНЕРАЦИЯ КОДОВ ====================
    
    def _extract_number(self, code: str, prefix: str) -> int:
        """Извлекает числовую часть из кода"""
        try:
            # Убираем префикс и пробелы
            num_part = code.replace(prefix, '').strip()
            return int(num_part)
        except:
            return 0
    
    def _get_next_code(self, prefix: str, type_name: str) -> str:
        """Генерирует следующий код для указанного типа"""
        # Фильтруем по типу
        mask = self.df_nomenclature['Тип'].str.lower() == type_name.lower()
        type_items = self.df_nomenclature[mask]
        
        max_num = 0
        for _, row in type_items.iterrows():
            code = row['Код']
            if code.startswith(prefix):
                num = self._extract_number(code, prefix)
                if num > max_num:
                    max_num = num
        
        next_num = max_num + 1
        
        # Определяем формат (3 или 4 цифры)
        if next_num > 999:
            return f"{prefix} {next_num}"
        else:
            return f"{prefix} {next_num:03d}"
    
    def get_next_product_code(self) -> str:
        """Генерирует следующий код для изделия"""
        return self._get_next_code('изд.', 'изделие')
    
    def get_next_node_code(self) -> str:
        """Генерирует следующий код для узла"""
        return self._get_next_code('узел', 'узел')
    
    def get_next_material_code(self) -> str:
        """Генерирует следующий код для материала"""
        return self._get_next_code('мат', 'материал')
    
    # ==================== ДОБАВЛЕНИЕ ====================
    
    def add_product(self, name: str, type_name: str, category: str = '', 
                   price: str = '0 ISK', multiplicity: int = 1) -> Tuple[bool, str, str]:
        """Добавляет новое изделие/узел с автоматическим кодом"""
        try:
            # Генерируем код в зависимости от типа
            if type_name.lower() == 'изделие':
                code = self.get_next_product_code()
            elif type_name.lower() == 'узел':
                code = self.get_next_node_code()
            else:
                return False, f"❌ Неизвестный тип: {type_name}", ""
            
            # Создаем новую запись
            new_row = pd.DataFrame([{
                'Код': code,
                'Наименование': name,
                'Тип': type_name,
                'Категории': category,
                'Цена производства': price,
                'Кратность': multiplicity
            }])
            
            self.df_nomenclature = pd.concat([self.df_nomenclature, new_row], ignore_index=True)
            
            return True, f"✅ {type_name} добавлено с кодом {code}", code
            
        except Exception as e:
            logger.error(f"Ошибка добавления {type_name}: {e}")
            return False, f"❌ Ошибка: {e}", ""
    
    def add_material(self, name: str, category: str = '') -> Tuple[bool, str, str]:
        """Добавляет новый материал с автоматическим кодом"""
        try:
            code = self.get_next_material_code()
            
            new_row = pd.DataFrame([{
                'Код': code,
                'Наименование': name,
                'Тип': 'материал',
                'Категории': category,
                'Цена производства': '',
                'Кратность': ''
            }])
            
            self.df_nomenclature = pd.concat([self.df_nomenclature, new_row], ignore_index=True)
            
            return True, f"✅ Материал добавлен с кодом {code}", code
            
        except Exception as e:
            logger.error(f"Ошибка добавления материала: {e}")
            return False, f"❌ Ошибка: {e}", ""
    
    # ==================== ПОЛУЧЕНИЕ ДАННЫХ ====================
    
    def get_product_by_code(self, code: str) -> Optional[Dict]:
        """Возвращает запись по коду"""
        mask = self.df_nomenclature['Код'] == code
        if mask.any():
            return self.df_nomenclature[mask].iloc[0].to_dict()
        return None
    
    def get_products_by_type(self, type_name: str, page: int = 0, per_page: int = 10) -> Tuple[List[Dict], int]:
        """Возвращает продукты определенного типа с пагинацией"""
        mask = self.df_nomenclature['Тип'].str.lower() == type_name.lower()
        filtered = self.df_nomenclature[mask]
        
        total = len(filtered)
        start = page * per_page
        end = min(start + per_page, total)
        
        items = []
        for _, row in filtered.iloc[start:end].iterrows():
            items.append({
                'code': row['Код'],
                'name': row['Наименование'],
                'category': row.get('Категории', '')
            })
        
        return items, total
    
    def get_products_by_category(self, category: str, page: int = 0, per_page: int = 10) -> Tuple[List[Dict], int]:
        """Возвращает продукты из категории с пагинацией"""
        mask = self.df_nomenclature['Категории'].str.contains(category, na=False)
        filtered = self.df_nomenclature[mask]
        
        total = len(filtered)
        start = page * per_page
        end = min(start + per_page, total)
        
        items = []
        for _, row in filtered.iloc[start:end].iterrows():
            items.append({
                'code': row['Код'],
                'name': row['Наименование'],
                'category': row.get('Категории', '')
            })
        
        return items, total
    
    # ==================== РЕДАКТИРОВАНИЕ ====================
    
    def update_product_field(self, code: str, field: str, value) -> Tuple[bool, str]:
        """Обновляет конкретное поле изделия/материала"""
        try:
            mask = self.df_nomenclature['Код'] == code
            if not mask.any():
                return False, f"❌ Запись с кодом {code} не найдена"
            
            self.df_nomenclature.loc[mask, field] = value
            return True, f"✅ Поле '{field}' обновлено"
            
        except Exception as e:
            logger.error(f"Ошибка обновления: {e}")
            return False, f"❌ Ошибка: {e}"
    
    # ==================== УДАЛЕНИЕ ====================
    
    def check_product_usage(self, code: str) -> Tuple[bool, List[str]]:
        """Проверяет, используется ли продукт в спецификациях"""
        used_in = []
        
        # Ищем как родителя (изделие/узел)
        as_parent = self.df_specifications[self.df_specifications['Родитель'] == code]
        for _, spec in as_parent.iterrows():
            child = spec['Потомок']
            child_name = self._get_name_by_code(child)
            used_in.append(f"📦 содержит: {child_name} ({child}) - {spec['Количество']} шт")
        
        # Ищем как потомка (материал/узел)
        as_child = self.df_specifications[self.df_specifications['Потомок'] == code]
        for _, spec in as_child.iterrows():
            parent = spec['Родитель']
            parent_name = self._get_name_by_code(parent)
            used_in.append(f"🔧 используется в: {parent_name} ({parent}) - {spec['Количество']} шт")
        
        return len(used_in) > 0, used_in
    
    def _get_name_by_code(self, code: str) -> str:
        """Получает наименование по коду"""
        mask = self.df_nomenclature['Код'] == code
        if mask.any():
            return self.df_nomenclature[mask].iloc[0]['Наименование']
        return "Неизвестно"
    
    def delete_product(self, code: str) -> Tuple[bool, str]:
        """Удаляет продукт и все связанные спецификации"""
        try:
            # Получаем информацию о продукте
            product = self.get_product_by_code(code)
            if not product:
                return False, f"❌ Запись с кодом {code} не найдена"
            
            product_name = product['Наименование']
            product_type = product['Тип']
            
            # Удаляем из номенклатуры
            self.df_nomenclature = self.df_nomenclature[self.df_nomenclature['Код'] != code]
            
            # Удаляем все спецификации, где этот код является родителем или потомком
            before_count = len(self.df_specifications)
            self.df_specifications = self.df_specifications[
                (self.df_specifications['Родитель'] != code) & 
                (self.df_specifications['Потомок'] != code)
            ]
            after_count = len(self.df_specifications)
            deleted_specs = before_count - after_count
            
            return True, f"✅ {product_type} '{product_name}' удален\nУдалено связанных спецификаций: {deleted_specs}"
            
        except Exception as e:
            logger.error(f"Ошибка удаления: {e}")
            return False, f"❌ Ошибка: {e}"
    
    # ==================== ПРИВЯЗКИ ====================
    
    def link_node_to_product(self, parent_code: str, node_code: str, quantity: int) -> Tuple[bool, str]:
        """Привязывает узел к изделию"""
        try:
            # Проверяем, нет ли уже такой связи
            existing = self.df_specifications[
                (self.df_specifications['Родитель'] == parent_code) & 
                (self.df_specifications['Потомок'] == node_code)
            ]
            
            if not existing.empty:
                return False, "❌ Такая связь уже существует"
            
            new_row = pd.DataFrame([{
                'Родитель': parent_code,
                'Потомок': node_code,
                'Количество': quantity
            }])
            
            self.df_specifications = pd.concat([self.df_specifications, new_row], ignore_index=True)
            
            return True, "✅ Узел привязан"
            
        except Exception as e:
            logger.error(f"Ошибка привязки узла: {e}")
            return False, f"❌ Ошибка: {e}"
    
    def link_material_to_product(self, parent_code: str, material_code: str, quantity: int) -> Tuple[bool, str]:
        """Привязывает материал к изделию/узлу"""
        try:
            # Проверяем, нет ли уже такой связи
            existing = self.df_specifications[
                (self.df_specifications['Родитель'] == parent_code) & 
                (self.df_specifications['Потомок'] == material_code)
            ]
            
            if not existing.empty:
                return False, "❌ Такая связь уже существует"
            
            new_row = pd.DataFrame([{
                'Родитель': parent_code,
                'Потомок': material_code,
                'Количество': quantity
            }])
            
            self.df_specifications = pd.concat([self.df_specifications, new_row], ignore_index=True)
            
            return True, "✅ Материал привязан"
            
        except Exception as e:
            logger.error(f"Ошибка привязки материала: {e}")
            return False, f"❌ Ошибка: {e}"
