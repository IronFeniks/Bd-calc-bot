import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import hashlib

from config import ADMIN_IDS, ITEMS_PER_PAGE
from keyboards import (
    main_menu_keyboard, categories_keyboard, products_keyboard,
    materials_keyboard, nodes_keyboard, product_detail_keyboard,
    material_detail_keyboard, cancel_button, back_button,
    confirm_keyboard, edit_product_fields_keyboard,
    edit_material_fields_keyboard, select_type_keyboard
)
from excel_handler import ExcelHandler
from states import AdminStates, get_user_data, set_user_state, get_user_state, clear_user_data

logger = logging.getLogger(__name__)

# Глобальный обработчик Excel
excel_handler = None

def set_excel_handler(handler: ExcelHandler):
    global excel_handler
    excel_handler = handler

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def extract_code_from_callback(data: str, prefix: str) -> str:
    """Извлекает код из callback_data (восстанавливает полный код)"""
    # Убираем префикс user_id_*
    parts = data.split('_', 2)
    if len(parts) < 3:
        return data
    
    code_part = parts[2].replace(prefix, '')
    
    # Пытаемся найти полный код в данных
    for _, row in excel_handler.df_nomenclature.iterrows():
        full_code = row['Код']
        # Проверяем по началу или по хэшу
        if full_code.startswith(code_part) or hashlib.md5(full_code.encode()).hexdigest()[:8] == code_part:
            return full_code
    
    return code_part

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этому боту.")
        return False
    return True

async def check_admin_callback(query, user_id) -> bool:
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ У вас нет доступа к этому боту", show_alert=True)
        return False
    return True

# ==================== ГЛАВНОЕ МЕНЮ ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    user_id = update.effective_user.id
    clear_user_data(context, user_id)
    set_user_state(context, user_id, AdminStates.MAIN_MENU)
    
    # Загружаем данные
    success, message = excel_handler.load_data()
    if not success:
        await update.message.reply_text(message)
        return
    
    text = (
        "🏭 УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ\n\n"
        "Выберите раздел для работы:\n"
        "• 📋 Категории\n"
        "• 🏗️ Изделия\n"
        "• 🔩 Узлы\n"
        "• ⚙️ Материалы"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(user_id)
    )

async def back_to_main(query, context, user_id):
    """Возврат в главное меню"""
    clear_user_data(context, user_id)
    set_user_state(context, user_id, AdminStates.MAIN_MENU)
    
    text = "🏭 УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ\n\nВыберите раздел для работы:"
    
    await query.edit_message_text(
        text,
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== КАТЕГОРИИ ====================

async def show_categories(query, context, user_id, page=1):
    """Показывает список категорий"""
    # Загружаем данные
    excel_handler.load_data()
    
    categories = excel_handler.get_unique_categories()
    total_items = len(categories)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    start = (page - 1) * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, total_items)
    page_categories = categories[start:end]
    
    set_user_state(context, user_id, AdminStates.CATEGORY_LIST)
    
    await query.edit_message_text(
        f"📋 КАТЕГОРИИ\n\nСтраница {page} из {total_pages}",
        reply_markup=categories_keyboard(page_categories, user_id, page, total_pages)
    )

async def add_category_start(query, context, user_id):
    """Начало добавления категории"""
    set_user_state(context, user_id, AdminStates.CATEGORY_ADD_NAME)
    
    await query.edit_message_text(
        "✏️ Добавление новой категории\n\n"
        "Введите название категории:",
        reply_markup=cancel_button(user_id)
    )

async def add_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Сохранение новой категории"""
    user_id = update.effective_user.id
    
    if not text or len(text) < 2:
        await update.message.reply_text(
            "❌ Название должно содержать минимум 2 символа. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    # Категории хранятся только в записях, поэтому просто сообщаем об успехе
    await update.message.reply_text(
        f"✅ Категория '{text}' будет доступна при создании элементов",
        reply_markup=back_button(user_id, "categories")
    )
    
    clear_user_data(context, user_id)

# ==================== ИЗДЕЛИЯ ====================

async def show_products(query, context, user_id, category=None, page=1):
    """Показывает список изделий"""
    excel_handler.load_data()
    
    if category == "Все" or not category:
        items, total_items = excel_handler.get_products_by_type('изделие', page-1, ITEMS_PER_PAGE)
    else:
        items, total_items = excel_handler.get_products_by_category(category, page-1, ITEMS_PER_PAGE)
        # Фильтруем только изделия
        items = [i for i in items if i.get('type') == 'изделие']
    
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    user_data = get_user_data(context, user_id)
    user_data['current_category'] = category
    
    set_user_state(context, user_id, AdminStates.PRODUCT_LIST)
    
    await query.edit_message_text(
        f"🏗️ ИЗДЕЛИЯ\n\nСтраница {page} из {total_pages}",
        reply_markup=products_keyboard(items, user_id, page, total_pages, category)
    )

async def show_nodes(query, context, user_id, page=1):
    """Показывает список узлов"""
    excel_handler.load_data()
    
    items, total_items = excel_handler.get_products_by_type('узел', page-1, ITEMS_PER_PAGE)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    set_user_state(context, user_id, AdminStates.NODE_LIST)
    
    await query.edit_message_text(
        f"🔩 УЗЛЫ\n\nСтраница {page} из {total_pages}",
        reply_markup=nodes_keyboard(items, user_id, page, total_pages)
    )

async def show_product_detail(query, context, user_id, product_code):
    """Показывает детали изделия/узла"""
    excel_handler.load_data()
    
    # Восстанавливаем полный код
    full_code = extract_code_from_callback(product_code, "product_")
    product = excel_handler.get_product_by_code(full_code)
    
    if not product:
        await query.edit_message_text("❌ Изделие не найдено")
        return
    
    user_data = get_user_data(context, user_id)
    user_data['current_product'] = full_code
    user_data['product_type'] = product['Тип']
    
    # Собираем информацию о составе
    nodes = []
    materials = []
    
    specs = excel_handler.df_specifications[
        excel_handler.df_specifications['Родитель'] == full_code
    ]
    
    for _, spec in specs.iterrows():
        child_code = spec['Потомок']
        quantity = spec['Количество']
        
        child = excel_handler.get_product_by_code(child_code)
        if child:
            if child['Тип'].lower() == 'узел':
                nodes.append(f"• {child['Наименование']} ({quantity} шт)")
            elif child['Тип'].lower() == 'материал':
                materials.append(f"• {child['Наименование']} ({quantity} шт)")
    
    # Формируем текст
    text = f"🏗️ {product['Тип']}: {product['Наименование']}\n\n"
    text += f"📌 Код: {product['Код']}\n"
    text += f"📂 Категория: {product.get('Категории', 'не указана')}\n"
    
    if product['Тип'].lower() == 'изделие':
        text += f"💰 Цена производства: {product.get('Цена производства', '0 ISK')}\n"
        text += f"🔢 Кратность: {product.get('Кратность', 1)}\n\n"
    else:
        text += f"💰 Цена производства: {product.get('Цена производства', '0 ISK')}\n\n"
    
    if nodes:
        text += "🔩 Узлы в составе:\n" + "\n".join(nodes) + "\n\n"
    else:
        text += "🔩 Узлы в составе: нет\n\n"
    
    if materials:
        text += "⚙️ Материалы в составе:\n" + "\n".join(materials) + "\n"
    else:
        text += "⚙️ Материалы в составе: нет"
    
    await query.edit_message_text(
        text,
        reply_markup=product_detail_keyboard(user_id, full_code, product['Тип'])
    )

async def add_product_start(query, context, user_id):
    """Начало добавления изделия"""
    user_data = get_user_data(context, user_id)
    user_data['new_item'] = {'type': 'изделие'}
    set_user_state(context, user_id, AdminStates.PRODUCT_ADD_NAME)
    
    await query.edit_message_text(
        "✏️ Добавление нового изделия\n\n"
        "Шаг 1 из 4: Введите название изделия:",
        reply_markup=cancel_button(user_id)
    )

async def add_node_start(query, context, user_id):
    """Начало добавления узла"""
    user_data = get_user_data(context, user_id)
    user_data['new_item'] = {'type': 'узел'}
    set_user_state(context, user_id, AdminStates.NODE_ADD_NAME)
    
    await query.edit_message_text(
        "✏️ Добавление нового узла\n\n"
        "Шаг 1 из 3: Введите название узла:",
        reply_markup=cancel_button(user_id)
    )

async def add_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, item_type: str):
    """Шаг 1: Ввод названия изделия/узла"""
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    if not text or len(text) < 2:
        await update.message.reply_text(
            "❌ Название должно содержать минимум 2 символа. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    user_data['new_item']['name'] = text
    
    # Переходим к выбору категории
    categories = excel_handler.get_unique_categories()
    
    if not categories:
        # Если нет категорий, пропускаем
        if item_type == 'изделие':
            user_data['new_item']['category'] = ''
            set_user_state(context, user_id, AdminStates.PRODUCT_ADD_PRICE)
            await update.message.reply_text(
                "Шаг 2 из 4: Введите цену производства (например: `5400000000 ISK`)",
                reply_markup=cancel_button(user_id)
            )
        else:  # узел
            user_data['new_item']['category'] = ''
            set_user_state(context, user_id, AdminStates.NODE_ADD_PRICE)
            await update.message.reply_text(
                "Шаг 2 из 3: Введите цену производства (например: `5400000000 ISK`)",
                reply_markup=cancel_button(user_id)
            )
        return
    
    # Показываем список категорий
    keyboard = []
    for cat in categories:
        cat_short = cat[:20]
        callback = f"user_{user_id}_cat_{cat_short}"
        keyboard.append([InlineKeyboardButton(cat, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data=f"user_{user_id}_cat_skip")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"user_{user_id}_cancel")])
    
    if item_type == 'изделие':
        set_user_state(context, user_id, AdminStates.PRODUCT_ADD_CATEGORY)
    else:
        set_user_state(context, user_id, AdminStates.NODE_ADD_CATEGORY)
    
    await update.message.reply_text(
        f"Шаг 2 из {4 if item_type == 'изделие' else 3}: Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    await add_item_name(update, context, text, 'изделие')

async def add_node_name(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    await add_item_name(update, context, text, 'узел')

async def select_category_callback(query, context, user_id, category, item_type):
    """Обработка выбора категории для изделия/узла"""
    user_data = get_user_data(context, user_id)
    
    if category != "skip":
        # Восстанавливаем полное название категории
        categories = excel_handler.get_unique_categories()
        for cat in categories:
            cat_short = cat[:20]
            if cat_short == category:
                user_data['new_item']['category'] = cat
                break
        else:
            user_data['new_item']['category'] = category
    else:
        user_data['new_item']['category'] = ''
    
    # Переходим к следующему шагу
    if item_type == 'изделие':
        set_user_state(context, user_id, AdminStates.PRODUCT_ADD_PRICE)
        await query.edit_message_text(
            "Шаг 3 из 4: Введите цену производства\n(например: `5400000000 ISK`)",
            reply_markup=cancel_button(user_id)
        )
    else:  # узел
        set_user_state(context, user_id, AdminStates.NODE_ADD_PRICE)
        await query.edit_message_text(
            "Шаг 3 из 3: Введите цену производства\n(например: `5400000000 ISK`)",
            reply_markup=cancel_button(user_id)
        )

async def add_item_price(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, item_type: str):
    """Шаг: Ввод цены для изделия/узла"""
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    user_data['new_item']['price'] = text
    
    if item_type == 'изделие':
        set_user_state(context, user_id, AdminStates.PRODUCT_ADD_MULTIPLICITY)
        await update.message.reply_text(
            "Шаг 4 из 4: Введите кратность (целое число, например: 10)",
            reply_markup=cancel_button(user_id)
        )
    else:  # узел
        # Сохраняем узел
        await save_item(update, context, user_id, item_type)

async def add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    await add_item_price(update, context, text, 'изделие')

async def add_node_price(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    await add_item_price(update, context, text, 'узел')

async def add_product_multiplicity(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Шаг: Ввод кратности для изделия"""
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    try:
        multiplicity = int(text)
        if multiplicity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Кратность должна быть целым положительным числом. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    user_data['new_item']['multiplicity'] = multiplicity
    await save_item(update, context, user_id, 'изделие')

async def save_item(update_or_query, context, user_id, item_type: str):
    """Сохранение нового изделия/узла"""
    user_data = get_user_data(context, user_id)
    new_item = user_data.get('new_item', {})
    
    # Добавляем в базу
    success, message, code = excel_handler.add_product(
        name=new_item['name'],
        type_name=item_type,
        category=new_item.get('category', ''),
        price=new_item.get('price', '0 ISK'),
        multiplicity=new_item.get('multiplicity', 1)
    )
    
    if success:
        # Сохраняем в Excel
        save_success, save_message = excel_handler.save_data()
        
        response_text = f"{message}\n\n"
        if save_success:
            response_text += "✅ Изменения сохранены в файл"
        else:
            response_text += f"❌ Ошибка сохранения: {save_message}"
        
        # Отправляем ответ
        if hasattr(update_or_query, 'message'):
            await update_or_query.message.reply_text(
                response_text,
                reply_markup=back_button(user_id, "products" if item_type == 'изделие' else "nodes")
            )
        else:
            await update_or_query.edit_message_text(
                response_text,
                reply_markup=back_button(user_id, "products" if item_type == 'изделие' else "nodes")
            )
    else:
        if hasattr(update_or_query, 'message'):
            await update_or_query.message.reply_text(
                message,
                reply_markup=cancel_button(user_id)
            )
        else:
            await update_or_query.edit_message_text(
                message,
                reply_markup=cancel_button(user_id)
            )
    
    clear_user_data(context, user_id)
# ==================== МАТЕРИАЛЫ ====================

async def show_materials(query, context, user_id, page=1):
    """Показывает список материалов"""
    excel_handler.load_data()
    
    items, total_items = excel_handler.get_products_by_type('материал', page-1, ITEMS_PER_PAGE)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    set_user_state(context, user_id, AdminStates.MATERIAL_LIST)
    
    await query.edit_message_text(
        f"⚙️ МАТЕРИАЛЫ\n\nСтраница {page} из {total_pages}",
        reply_markup=materials_keyboard(items, user_id, page, total_pages)
    )

async def show_material_detail(query, context, user_id, material_code):
    """Показывает детали материала"""
    excel_handler.load_data()
    
    # Восстанавливаем полный код
    full_code = extract_code_from_callback(material_code, "material_")
    material = excel_handler.get_product_by_code(full_code)
    
    if not material:
        await query.edit_message_text("❌ Материал не найден")
        return
    
    user_data = get_user_data(context, user_id)
    user_data['current_material'] = full_code
    
    # Проверяем, где используется
    used_in = excel_handler.df_specifications[
        excel_handler.df_specifications['Потомок'] == full_code
    ]
    
    text = f"⚙️ Материал: {material['Наименование']}\n\n"
    text += f"📌 Код: {material['Код']}\n"
    text += f"📂 Категория: {material.get('Категории', 'не указана')}\n\n"
    
    if len(used_in) > 0:
        text += "🔧 Используется в:\n"
        for _, spec in used_in.iterrows():
            parent_code = spec['Родитель']
            quantity = spec['Количество']
            
            parent = excel_handler.get_product_by_code(parent_code)
            if parent:
                text += f"• {parent['Наименование']} ({quantity} шт)\n"
    else:
        text += "🔧 Используется в: нигде"
    
    await query.edit_message_text(
        text,
        reply_markup=material_detail_keyboard(user_id, full_code)
    )

async def add_material_start(query, context, user_id):
    """Начало добавления материала"""
    user_data = get_user_data(context, user_id)
    user_data['new_material'] = {}
    set_user_state(context, user_id, AdminStates.MATERIAL_ADD_NAME)
    
    await query.edit_message_text(
        "✏️ Добавление нового материала\n\n"
        "Шаг 1 из 2: Введите название материала:",
        reply_markup=cancel_button(user_id)
    )

async def add_material_name(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Шаг 1: Ввод названия материала"""
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    if not text or len(text) < 2:
        await update.message.reply_text(
            "❌ Название должно содержать минимум 2 символа. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    user_data['new_material']['name'] = text
    
    # Переходим к выбору категории
    categories = excel_handler.get_unique_categories()
    
    if not categories:
        # Если нет категорий, сохраняем сразу
        await save_material(update, context, user_id, '')
        return
    
    # Показываем список категорий
    keyboard = []
    for cat in categories:
        cat_short = cat[:20]
        callback = f"user_{user_id}_matcat_{cat_short}"
        keyboard.append([InlineKeyboardButton(cat, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data=f"user_{user_id}_matcat_skip")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"user_{user_id}_cancel")])
    
    set_user_state(context, user_id, AdminStates.MATERIAL_ADD_CATEGORY)
    
    await update.message.reply_text(
        "Шаг 2 из 2: Выберите категорию (необязательно):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_material_category_callback(query, context, user_id, category):
    """Обработка выбора категории для материала"""
    await save_material(query, context, user_id, category)

async def save_material(update_or_query, context, user_id, category):
    """Сохранение нового материала"""
    user_data = get_user_data(context, user_id)
    new_material = user_data.get('new_material', {})
    
    if category != "skip":
        # Восстанавливаем полное название категории
        categories = excel_handler.get_unique_categories()
        for cat in categories:
            cat_short = cat[:20]
            if cat_short == category:
                category = cat
                break
    
    # Добавляем в базу
    success, message, code = excel_handler.add_material(
        name=new_material['name'],
        category=category if category != "skip" else ''
    )
    
    if success:
        # Сохраняем в Excel
        save_success, save_message = excel_handler.save_data()
        
        response_text = f"{message}\n\n"
        if save_success:
            response_text += "✅ Изменения сохранены в файл"
        else:
            response_text += f"❌ Ошибка сохранения: {save_message}"
        
        if hasattr(update_or_query, 'message'):
            await update_or_query.message.reply_text(
                response_text,
                reply_markup=back_button(user_id, "materials")
            )
        else:
            await update_or_query.edit_message_text(
                response_text,
                reply_markup=back_button(user_id, "materials")
            )
    else:
        if hasattr(update_or_query, 'message'):
            await update_or_query.message.reply_text(
                message,
                reply_markup=cancel_button(user_id)
            )
        else:
            await update_or_query.edit_message_text(
                message,
                reply_markup=cancel_button(user_id)
            )
    
    clear_user_data(context, user_id)

# ==================== РЕДАКТИРОВАНИЕ ====================

async def edit_product_start(query, context, user_id, product_code):
    """Начало редактирования изделия/узла"""
    full_code = extract_code_from_callback(product_code, "edit_product_")
    product = excel_handler.get_product_by_code(full_code)
    
    if not product:
        await query.edit_message_text("❌ Изделие не найдено")
        return
    
    user_data = get_user_data(context, user_id)
    user_data['editing_item'] = {
        'code': full_code,
        'type': product['Тип']
    }
    
    await query.edit_message_text(
        f"✏️ Редактирование: {product['Наименование']}\n\n"
        f"Выберите поле для изменения:",
        reply_markup=edit_product_fields_keyboard(user_id, full_code)
    )

async def edit_material_start(query, context, user_id, material_code):
    """Начало редактирования материала"""
    full_code = extract_code_from_callback(material_code, "edit_material_")
    material = excel_handler.get_product_by_code(full_code)
    
    if not material:
        await query.edit_message_text("❌ Материал не найден")
        return
    
    user_data = get_user_data(context, user_id)
    user_data['editing_item'] = {
        'code': full_code,
        'type': 'материал'
    }
    
    await query.edit_message_text(
        f"✏️ Редактирование: {material['Наименование']}\n\n"
        f"Выберите поле для изменения:",
        reply_markup=edit_material_fields_keyboard(user_id, full_code)
    )

async def edit_field_start(query, context, user_id, field, item_code):
    """Начало редактирования конкретного поля"""
    full_code = extract_code_from_callback(item_code, f"edit_field_{field}_")
    item = excel_handler.get_product_by_code(full_code)
    
    if not item:
        await query.edit_message_text("❌ Запись не найдена")
        return
    
    user_data = get_user_data(context, user_id)
    user_data['editing_field'] = {
        'code': full_code,
        'field': field,
        'current_value': item.get(field_mapping(field), '')
    }
    
    # Устанавливаем соответствующий state
    state_map = {
        'name': AdminStates.EDIT_NAME,
        'category': AdminStates.EDIT_CATEGORY,
        'price': AdminStates.EDIT_PRICE,
        'multiplicity': AdminStates.EDIT_MULTIPLICITY
    }
    
    set_user_state(context, user_id, state_map.get(field, AdminStates.EDIT_NAME))
    
    # Запрашиваем новое значение
    prompts = {
        'name': "Введите новое название:",
        'category': "Введите новую категорию:",
        'price': "Введите новую цену производства (например: `5400000000 ISK`):",
        'multiplicity': "Введите новую кратность (целое число):"
    }
    
    await query.edit_message_text(
        f"✏️ Редактирование поля '{field}'\n\n"
        f"Текущее значение: {user_data['editing_field']['current_value']}\n\n"
        f"{prompts.get(field, 'Введите новое значение:')}",
        reply_markup=cancel_button(user_id)
    )

def field_mapping(field: str) -> str:
    """Маппинг названий полей"""
    mapping = {
        'name': 'Наименование',
        'category': 'Категории',
        'price': 'Цена производства',
        'multiplicity': 'Кратность'
    }
    return mapping.get(field, field)

async def edit_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Сохранение отредактированного поля"""
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    editing = user_data.get('editing_field', {})
    if not editing:
        await update.message.reply_text("❌ Ошибка: нет данных для редактирования")
        return
    
    # Валидация для特定ных полей
    if editing['field'] == 'multiplicity':
        try:
            value = int(text)
            if value <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "❌ Кратность должна быть целым положительным числом. Попробуйте ещё раз:",
                reply_markup=cancel_button(user_id)
            )
            return
    else:
        value = text
    
    # Обновляем в базе
    field_name = field_mapping(editing['field'])
    success, message = excel_handler.update_product_field(editing['code'], field_name, value)
    
    if success:
        # Сохраняем в Excel
        save_success, save_message = excel_handler.save_data()
        
        response_text = f"{message}\n\n"
        if save_success:
            response_text += "✅ Изменения сохранены в файл"
        else:
            response_text += f"❌ Ошибка сохранения: {save_message}"
        
        # Возвращаемся к деталям
        item = excel_handler.get_product_by_code(editing['code'])
        if item['Тип'].lower() == 'материал':
            await update.message.reply_text(
                response_text,
                reply_markup=back_button(user_id, f"material_{editing['code']}")
            )
        else:
            await update.message.reply_text(
                response_text,
                reply_markup=back_button(user_id, f"product_{editing['code']}")
            )
    else:
        await update.message.reply_text(
            message,
            reply_markup=cancel_button(user_id)
        )
    
    clear_user_data(context, user_id)

# ==================== УДАЛЕНИЕ С ПОДТВЕРЖДЕНИЕМ ====================

async def delete_product_start(query, context, user_id, product_code):
    """Начало удаления изделия/узла"""
    full_code = extract_code_from_callback(product_code, "delete_product_")
    product = excel_handler.get_product_by_code(full_code)
    
    if not product:
        await query.edit_message_text("❌ Изделие не найдено")
        return
    
    # Проверяем, используется ли где-то
    is_used, usage_list = excel_handler.check_product_usage(full_code)
    
    text = f"🗑️ Удаление: {product['Наименование']}\n\n"
    
    if is_used:
        text += "⚠️ *ВНИМАНИЕ!* Этот элемент используется в других изделиях:\n\n"
        text += "\n".join(usage_list)
        text += "\n\nПри удалении все связи будут разорваны!\n\n"
    else:
        text += "Этот элемент нигде не используется.\n\n"
    
    text += "Вы уверены, что хотите удалить?"
    
    await query.edit_message_text(
        text,
        reply_markup=confirm_keyboard(user_id, "delete", full_code),
        parse_mode='Markdown'
    )

async def delete_material_start(query, context, user_id, material_code):
    """Начало удаления материала"""
    full_code = extract_code_from_callback(material_code, "delete_material_")
    material = excel_handler.get_product_by_code(full_code)
    
    if not material:
        await query.edit_message_text("❌ Материал не найден")
        return
    
    # Проверяем, используется ли где-то
    is_used, usage_list = excel_handler.check_product_usage(full_code)
    
    text = f"🗑️ Удаление: {material['Наименование']}\n\n"
    
    if is_used:
        text += "⚠️ *ВНИМАНИЕ!* Этот материал используется в:\n\n"
        text += "\n".join(usage_list)
        text += "\n\nПри удалении все связи будут разорваны!\n\n"
    else:
        text += "Этот материал нигде не используется.\n\n"
    
    text += "Вы уверены, что хотите удалить?"
    
    await query.edit_message_text(
        text,
        reply_markup=confirm_keyboard(user_id, "delete", full_code),
        parse_mode='Markdown'
    )

async def confirm_delete(query, context, user_id, item_code):
    """Подтверждение удаления"""
    full_code = extract_code_from_callback(item_code, "confirm_delete_")
    
    # Удаляем
    success, message = excel_handler.delete_product(full_code)
    
    if success:
        # Сохраняем в Excel
        save_success, save_message = excel_handler.save_data()
        
        response_text = f"{message}\n\n"
        if save_success:
            response_text += "✅ Изменения сохранены в файл"
        else:
            response_text += f"❌ Ошибка сохранения: {save_message}"
        
        # Возвращаемся к списку
        item = excel_handler.get_product_by_code(full_code)
        if item and item['Тип'].lower() == 'материал':
            await query.edit_message_text(
                response_text,
                reply_markup=back_button(user_id, "materials")
            )
        else:
            await query.edit_message_text(
                response_text,
                reply_markup=back_button(user_id, "products")
            )
    else:
        await query.edit_message_text(
            message,
            reply_markup=back_button(user_id, "main")
        )

# ==================== ПРИВЯЗКА УЗЛОВ И МАТЕРИАЛОВ ====================

async def link_node_start(query, context, user_id, product_code):
    """Начало привязки узла к изделию"""
    full_code = extract_code_from_callback(product_code, "link_node_")
    
    user_data = get_user_data(context, user_id)
    user_data['link_parent'] = full_code
    set_user_state(context, user_id, AdminStates.PRODUCT_LINK_NODE_SELECT)
    
    # Получаем список всех узлов
    nodes, _ = excel_handler.get_products_by_type('узел', 0, 1000)
    
    if not nodes:
        await query.edit_message_text(
            "❌ Нет доступных узлов для привязки",
            reply_markup=back_button(user_id, f"product_{full_code}")
        )
        return
    
    keyboard = []
    for node in nodes[:20]:  # Ограничиваем 20 для избежания длинного сообщения
        callback = f"user_{user_id}_selnode_{node['code'][:15]}"
        keyboard.append([InlineKeyboardButton(
            f"{node['code']} - {node['name'][:30]}",
            callback_data=callback
        )])
    
    if len(nodes) > 20:
        keyboard.append([InlineKeyboardButton("➡️ Далее", callback_data=f"user_{user_id}_nodes_page_2")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"user_{user_id}_cancel")])
    
    await query.edit_message_text(
        "🔗 Привязка узла к изделию\n\n"
        "Выберите узел из списка:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def link_material_start(query, context, user_id, product_code):
    """Начало привязки материала к изделию/узлу"""
    full_code = extract_code_from_callback(product_code, "link_material_")
    
    user_data = get_user_data(context, user_id)
    user_data['link_parent'] = full_code
    set_user_state(context, user_id, AdminStates.PRODUCT_LINK_MATERIAL_SELECT)
    
    # Получаем список всех материалов
    materials, _ = excel_handler.get_products_by_type('материал', 0, 1000)
    
    if not materials:
        await query.edit_message_text(
            "❌ Нет доступных материалов для привязки",
            reply_markup=back_button(user_id, f"product_{full_code}")
        )
        return
    
    keyboard = []
    for material in materials[:20]:
        callback = f"user_{user_id}_selmat_{material['code'][:15]}"
        keyboard.append([InlineKeyboardButton(
            f"{material['code']} - {material['name'][:30]}",
            callback_data=callback
        )])
    
    if len(materials) > 20:
        keyboard.append([InlineKeyboardButton("➡️ Далее", callback_data=f"user_{user_id}_materials_page_2")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"user_{user_id}_cancel")])
    
    await query.edit_message_text(
        "⚙️ Привязка материала\n\n"
        "Выберите материал из списка:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_node_callback(query, context, user_id, node_code):
    """Выбор узла для привязки"""
    full_code = extract_code_from_callback(node_code, "selnode_")
    
    user_data = get_user_data(context, user_id)
    user_data['link_child'] = full_code
    set_user_state(context, user_id, AdminStates.PRODUCT_LINK_NODE_QUANTITY)
    
    await query.edit_message_text(
        "✏️ Введите количество узлов (шт):",
        reply_markup=cancel_button(user_id)
    )

async def select_material_callback(query, context, user_id, material_code):
    """Выбор материала для привязки"""
    full_code = extract_code_from_callback(material_code, "selmat_")
    
    user_data = get_user_data(context, user_id)
    user_data['link_child'] = full_code
    set_user_state(context, user_id, AdminStates.PRODUCT_LINK_MATERIAL_QUANTITY)
    
    await query.edit_message_text(
        "✏️ Введите количество материала (шт):",
        reply_markup=cancel_button(user_id)
    )

async def link_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, link_type: str):
    """Сохранение количества при привязке"""
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Введите целое положительное число. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    parent_code = user_data.get('link_parent')
    child_code = user_data.get('link_child')
    
    if link_type == 'node':
        success, message = excel_handler.link_node_to_product(parent_code, child_code, quantity)
    else:
        success, message = excel_handler.link_material_to_product(parent_code, child_code, quantity)
    
    if success:
        save_success, save_message = excel_handler.save_data()
        
        response_text = f"{message}\n\n"
        if save_success:
            response_text += "✅ Изменения сохранены в файл"
        else:
            response_text += f"❌ Ошибка сохранения: {save_message}"
        
        await update.message.reply_text(
            response_text,
            reply_markup=back_button(user_id, f"product_{parent_code}")
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=cancel_button(user_id)
        )
    
    clear_user_data(context, user_id)

async def link_node_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    await link_quantity(update, context, text, 'node')

async def link_material_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    await link_quantity(update, context, text, 'material')
# ==================== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    logger.info(f"📨 Сообщение от {user_id}: {update.message.text[:50]}...")
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этому боту.")
        return
    
    user_data = get_user_data(context, user_id)
    state = get_user_state(context, user_id)
    text = update.message.text.strip()
    
    # Обработка в зависимости от состояния
    if state == AdminStates.CATEGORY_ADD_NAME:
        await add_category_name(update, context, text)
        return
    
    # Изделия
    if state == AdminStates.PRODUCT_ADD_NAME:
        await add_product_name(update, context, text)
        return
    if state == AdminStates.PRODUCT_ADD_PRICE:
        await add_product_price(update, context, text)
        return
    if state == AdminStates.PRODUCT_ADD_MULTIPLICITY:
        await add_product_multiplicity(update, context, text)
        return
    
    # Узлы
    if state == AdminStates.NODE_ADD_NAME:
        await add_node_name(update, context, text)
        return
    if state == AdminStates.NODE_ADD_PRICE:
        await add_node_price(update, context, text)
        return
    
    # Материалы
    if state == AdminStates.MATERIAL_ADD_NAME:
        await add_material_name(update, context, text)
        return
    
    # Привязки
    if state == AdminStates.PRODUCT_LINK_NODE_QUANTITY:
        await link_node_quantity(update, context, text)
        return
    if state == AdminStates.PRODUCT_LINK_MATERIAL_QUANTITY:
        await link_material_quantity(update, context, text)
        return
    
    # Редактирование
    if state in [AdminStates.EDIT_NAME, AdminStates.EDIT_CATEGORY, 
                 AdminStates.EDIT_PRICE, AdminStates.EDIT_MULTIPLICITY]:
        await edit_field_value(update, context, text)
        return
    
    # Если состояние не определено
    await update.message.reply_text(
        "❓ Я ожидаю команды из меню. Используйте /start",
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== ОБРАБОТЧИК КНОПОК ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик callback кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Пропускаем noop
    if data == "noop":
        return
    
    # Проверяем, что кнопка для этого пользователя
    if not data.startswith(f"user_{user_id}_") and data != "noop":
        await query.answer("⛔ Эта кнопка не для вас", show_alert=True)
        return
    
    # Проверяем права админа
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ У вас нет доступа", show_alert=True)
        return
    
    # Убираем префикс с user_id
    action = data.replace(f"user_{user_id}_", "")
    
    # ===== ГЛОБАЛЬНЫЕ ДЕЙСТВИЯ =====
    if action == "main":
        await back_to_main(query, context, user_id)
        return
    
    if action == "exit":
        await query.edit_message_text("👋 До свидания!")
        return
    
    if action == "cancel":
        clear_user_data(context, user_id)
        set_user_state(context, user_id, AdminStates.MAIN_MENU)
        await query.edit_message_text(
            "❌ Действие отменено",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    # ===== НАВИГАЦИЯ ПО РАЗДЕЛАМ =====
    if action == "categories":
        await show_categories(query, context, user_id, 1)
        return
    
    if action == "products":
        await show_products(query, context, user_id, "Все", 1)
        return
    
    if action == "nodes":
        await show_nodes(query, context, user_id, 1)
        return
    
    if action == "materials":
        await show_materials(query, context, user_id, 1)
        return
    
    # ===== НАВИГАЦИЯ НАЗАД =====
    if action.startswith("back_to_"):
        target = action.replace("back_to_", "")
        
        if target == "categories":
            await show_categories(query, context, user_id, 1)
        elif target == "products":
            await show_products(query, context, user_id, "Все", 1)
        elif target == "nodes":
            await show_nodes(query, context, user_id, 1)
        elif target == "materials":
            await show_materials(query, context, user_id, 1)
        elif target.startswith("product_"):
            code = target.replace("product_", "")
            await show_product_detail(query, context, user_id, code)
        elif target.startswith("material_"):
            code = target.replace("material_", "")
            await show_material_detail(query, context, user_id, code)
        else:
            await back_to_main(query, context, user_id)
        return
    
    # ===== КАТЕГОРИИ =====
    if action.startswith("categories_page_"):
        page = int(action.replace("categories_page_", ""))
        await show_categories(query, context, user_id, page)
        return
    
    if action == "add_category":
        await add_category_start(query, context, user_id)
        return
    
    if action.startswith("cat_"):
        category = action[4:]
        user_data = get_user_data(context, user_id)
        user_data['current_category'] = category
        await show_products(query, context, user_id, category, 1)
        return
    
    # ===== ИЗДЕЛИЯ =====
    if action.startswith("products_page_"):
        page = int(action.replace("products_page_", ""))
        user_data = get_user_data(context, user_id)
        category = user_data.get('current_category', "Все")
        await show_products(query, context, user_id, category, page)
        return
    
    if action == "add_product":
        await add_product_start(query, context, user_id)
        return
    
    if action.startswith("product_"):
        code = action.replace("product_", "")
        await show_product_detail(query, context, user_id, code)
        return
    
    # ===== УЗЛЫ =====
    if action.startswith("nodes_page_"):
        page = int(action.replace("nodes_page_", ""))
        await show_nodes(query, context, user_id, page)
        return
    
    if action == "add_node":
        await add_node_start(query, context, user_id)
        return
    
    if action.startswith("node_"):
        code = action.replace("node_", "")
        await show_product_detail(query, context, user_id, code)
        return
    
    # ===== МАТЕРИАЛЫ =====
    if action.startswith("materials_page_"):
        page = int(action.replace("materials_page_", ""))
        await show_materials(query, context, user_id, page)
        return
    
    if action == "add_material":
        await add_material_start(query, context, user_id)
        return
    
    if action.startswith("material_"):
        code = action.replace("material_", "")
        await show_material_detail(query, context, user_id, code)
        return
    
    # ===== РЕДАКТИРОВАНИЕ =====
    if action.startswith("edit_product_"):
        code = action.replace("edit_product_", "")
        await edit_product_start(query, context, user_id, code)
        return
    
    if action.startswith("edit_material_"):
        code = action.replace("edit_material_", "")
        await edit_material_start(query, context, user_id, code)
        return
    
    if action.startswith("edit_field_"):
        # Формат: edit_field_name_code
        parts = action.split('_')
        if len(parts) >= 4:
            field = parts[2]
            code = '_'.join(parts[3:])
            await edit_field_start(query, context, user_id, field, code)
        return
    
    # ===== УДАЛЕНИЕ =====
    if action.startswith("delete_product_"):
        code = action.replace("delete_product_", "")
        await delete_product_start(query, context, user_id, code)
        return
    
    if action.startswith("delete_material_"):
        code = action.replace("delete_material_", "")
        await delete_material_start(query, context, user_id, code)
        return
    
    if action.startswith("confirm_delete_"):
        code = action.replace("confirm_delete_", "")
        await confirm_delete(query, context, user_id, code)
        return
    
    # ===== ПРИВЯЗКИ =====
    if action.startswith("link_node_"):
        code = action.replace("link_node_", "")
        await link_node_start(query, context, user_id, code)
        return
    
    if action.startswith("link_material_"):
        code = action.replace("link_material_", "")
        await link_material_start(query, context, user_id, code)
        return
    
    if action.startswith("selnode_"):
        code = action.replace("selnode_", "")
        await select_node_callback(query, context, user_id, code)
        return
    
    if action.startswith("selmat_"):
        code = action.replace("selmat_", "")
        await select_material_callback(query, context, user_id, code)
        return
    
    # ===== ВЫБОР КАТЕГОРИИ ПРИ СОЗДАНИИ =====
    if action.startswith("cat_") and not action.startswith("categories_"):
        category = action[4:]
        user_data = get_user_data(context, user_id)
        item_type = user_data.get('new_item', {}).get('type', 'изделие')
        await select_category_callback(query, context, user_id, category, item_type)
        return
    
    if action == "cat_skip":
        await select_category_callback(query, context, user_id, "skip", 
                                      user_data.get('new_item', {}).get('type', 'изделие'))
        return
    
    if action.startswith("matcat_"):
        category = action[7:]
        await select_material_category_callback(query, context, user_id, category)
        return
    
    if action == "matcat_skip":
        await select_material_category_callback(query, context, user_id, "skip")
        return
    
    logger.warning(f"Неизвестный callback: {action}")
    await query.answer("❌ Неизвестная команда", show_alert=True)

# ==================== ФАЙЛ states.py ====================

"""
Модуль для управления состояниями пользователей в боте
"""

from enum import Enum, auto
from typing import Dict, Any, Optional
from telegram.ext import ContextTypes

class AdminStates(Enum):
    """Состояния для административного бота"""
    # Общие
    MAIN_MENU = auto()
    
    # Категории
    CATEGORY_LIST = auto()
    CATEGORY_ADD_NAME = auto()
    
    # Изделия
    PRODUCT_LIST = auto()
    PRODUCT_ADD_NAME = auto()
    PRODUCT_ADD_CATEGORY = auto()
    PRODUCT_ADD_PRICE = auto()
    PRODUCT_ADD_MULTIPLICITY = auto()
    
    # Узлы
    NODE_LIST = auto()
    NODE_ADD_NAME = auto()
    NODE_ADD_CATEGORY = auto()
    NODE_ADD_PRICE = auto()
    
    # Материалы
    MATERIAL_LIST = auto()
    MATERIAL_ADD_NAME = auto()
    MATERIAL_ADD_CATEGORY = auto()
    
    # Привязки
    PRODUCT_LINK_NODE_SELECT = auto()
    PRODUCT_LINK_NODE_QUANTITY = auto()
    PRODUCT_LINK_MATERIAL_SELECT = auto()
    PRODUCT_LINK_MATERIAL_QUANTITY = auto()
    
    # Редактирование
    EDIT_NAME = auto()
    EDIT_CATEGORY = auto()
    EDIT_PRICE = auto()
    EDIT_MULTIPLICITY = auto()

# Хранилище данных пользователей (в памяти)
_user_data: Dict[int, Dict[str, Any]] = {}
_user_states: Dict[int, AdminStates] = {}

def get_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> Dict[str, Any]:
    """Получает данные пользователя"""
    if user_id not in _user_data:
        _user_data[user_id] = {}
    return _user_data[user_id]

def set_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int, data: Dict[str, Any]):
    """Устанавливает данные пользователя"""
    _user_data[user_id] = data

def clear_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Очищает данные пользователя"""
    if user_id in _user_data:
        del _user_data[user_id]
    if user_id in _user_states:
        del _user_states[user_id]

def get_user_state(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> Optional[AdminStates]:
    """Получает состояние пользователя"""
    return _user_states.get(user_id)

def set_user_state(context: ContextTypes.DEFAULT_TYPE, user_id: int, state: AdminStates):
    """Устанавливает состояние пользователя"""
    _user_states[user_id] = state

# ==================== ОБНОВЛЕННЫЙ main.py ====================

"""
Главный файл для запуска бота управления базой данных
"""

import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import TOKEN
from excel_handler import ExcelHandler
from handlers import (
    start_command, button_handler, handle_message,
    set_excel_handler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Запуск бота"""
    # Путь к файлу Excel
    excel_path = 'data/База для приложения.xlsx'
    
    # Создаем обработчик Excel
    excel_handler = ExcelHandler(excel_path)
    
    # Передаем его в handlers
    set_excel_handler(excel_handler)
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Бот управления базой данных запущен")
    logger.info(f"📁 Файл Excel: {excel_path}")
    
    # Запускаем бота
    app.run_polling()

if __name__ == '__main__':
    main()
