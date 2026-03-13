from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import hashlib

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def make_callback(user_id, action, data=""):
    """Создаёт callback_data с проверкой длины"""
    if data:
        base = f"user_{user_id}_{action}_{data}"
    else:
        base = f"user_{user_id}_{action}"
    
    if len(base.encode()) <= 64:
        return base
    
    # Если длинно, берём хэш
    data_hash = hashlib.md5(data.encode()).hexdigest()[:8]
    return f"user_{user_id}_{action}_{data_hash}"

# ==================== БАЗОВЫЕ КНОПКИ ====================

def cancel_button(user_id):
    """Кнопка отмены"""
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]]
    return InlineKeyboardMarkup(keyboard)

def back_button(user_id, to):
    """Кнопка назад с указанием куда"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, f"back_to_{to}"))],
        [InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]
    ]
    return InlineKeyboardMarkup(keyboard)

def confirm_keyboard(user_id, action, item_code):
    """Клавиатура подтверждения действия"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, подтверждаю", callback_data=make_callback(user_id, f"confirm_{action}", item_code)),
            InlineKeyboardButton("❌ Нет, отмена", callback_data=make_callback(user_id, "cancel"))
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def edit_field_keyboard(user_id, item_code, fields):
    """Клавиатура выбора поля для редактирования"""
    keyboard = []
    for field_name, field_action in fields:
        keyboard.append([InlineKeyboardButton(
            field_name, 
            callback_data=make_callback(user_id, f"edit_field_{field_action}", item_code)
        )])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    return InlineKeyboardMarkup(keyboard)

# ==================== ГЛАВНОЕ МЕНЮ ====================

def main_menu_keyboard(user_id):
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("📋 Категории", callback_data=make_callback(user_id, "categories"))],
        [InlineKeyboardButton("🏗️ Изделия", callback_data=make_callback(user_id, "products"))],
        [InlineKeyboardButton("🔩 Узлы", callback_data=make_callback(user_id, "nodes"))],
        [InlineKeyboardButton("⚙️ Материалы", callback_data=make_callback(user_id, "materials"))],
        [InlineKeyboardButton("🚪 Выход", callback_data=make_callback(user_id, "exit"))]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== КАТЕГОРИИ ====================

def categories_keyboard(categories, user_id, current_page, total_pages):
    """Клавиатура списка категорий"""
    keyboard = []
    
    # Кнопки категорий
    for cat in categories:
        cat_short = cat[:20]  # Обрезаем для callback
        keyboard.append([InlineKeyboardButton(
            f"📁 {cat}", 
            callback_data=make_callback(user_id, "cat", cat_short)
        )])
    
    # Навигация
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "categories_page", str(current_page-1))))
    nav_row.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "categories_page", str(current_page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    # Управление
    keyboard.append([InlineKeyboardButton("➕ Добавить категорию", callback_data=make_callback(user_id, "add_category"))])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data=make_callback(user_id, "main"))])
    
    return InlineKeyboardMarkup(keyboard)

# ==================== ИЗДЕЛИЯ ====================

def products_keyboard(products, user_id, current_page, total_pages, category=None):
    """Клавиатура списка изделий"""
    keyboard = []
    
    # Кнопки изделий
    for p in products:
        code_short = p['code'][:15]  # Обрезаем для callback
        name = p['name'][:30] + "..." if len(p['name']) > 30 else p['name']
        keyboard.append([InlineKeyboardButton(
            f"{p['code']} - {name}", 
            callback_data=make_callback(user_id, "product", code_short)
        )])
    
    # Навигация
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "products_page", str(current_page-1))))
    nav_row.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "products_page", str(current_page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    # Управление
    keyboard.append([InlineKeyboardButton("➕ Добавить изделие", callback_data=make_callback(user_id, "add_product"))])
    
    back_row = []
    if category and category != "Все":
        back_row.append(InlineKeyboardButton("🔙 К категориям", callback_data=make_callback(user_id, "categories")))
    back_row.append(InlineKeyboardButton("🔙 Главное меню", callback_data=make_callback(user_id, "main")))
    keyboard.append(back_row)
    
    return InlineKeyboardMarkup(keyboard)

# ==================== УЗЛЫ ====================

def nodes_keyboard(nodes, user_id, current_page, total_pages):
    """Клавиатура списка узлов"""
    keyboard = []
    
    for node in nodes:
        code_short = node['code'][:15]
        name = node['name'][:30] + "..." if len(node['name']) > 30 else node['name']
        keyboard.append([InlineKeyboardButton(
            f"{node['code']} - {name}", 
            callback_data=make_callback(user_id, "node", code_short)
        )])
    
    # Навигация
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "nodes_page", str(current_page-1))))
    nav_row.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "nodes_page", str(current_page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("➕ Добавить узел", callback_data=make_callback(user_id, "add_node"))])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data=make_callback(user_id, "main"))])
    
    return InlineKeyboardMarkup(keyboard)

# ==================== МАТЕРИАЛЫ ====================

def materials_keyboard(materials, user_id, current_page, total_pages):
    """Клавиатура списка материалов"""
    keyboard = []
    
    for m in materials:
        code_short = m['code'][:15]
        name = m['name'][:30] + "..." if len(m['name']) > 30 else m['name']
        keyboard.append([InlineKeyboardButton(
            f"{m['code']} - {name}", 
            callback_data=make_callback(user_id, "material", code_short)
        )])
    
    # Навигация
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "materials_page", str(current_page-1))))
    nav_row.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "materials_page", str(current_page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("➕ Добавить материал", callback_data=make_callback(user_id, "add_material"))])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data=make_callback(user_id, "main"))])
    
    return InlineKeyboardMarkup(keyboard)

# ==================== ДЕТАЛИ С КНОПКАМИ РЕДАКТИРОВАНИЯ ====================

def product_detail_keyboard(user_id, product_code, product_type):
    """Клавиатура деталей изделия/узла с кнопками действий"""
    code_short = product_code[:15]
    
    keyboard = [
        [
            InlineKeyboardButton("✏️ Редактировать", callback_data=make_callback(user_id, "edit_product", code_short)),
            InlineKeyboardButton("🗑️ Удалить", callback_data=make_callback(user_id, "delete_product", code_short))
        ],
        [InlineKeyboardButton("🔗 Привязать узел", callback_data=make_callback(user_id, "link_node", code_short))],
        [InlineKeyboardButton("⚙️ Привязать материал", callback_data=make_callback(user_id, "link_material", code_short))],
        [InlineKeyboardButton("🔙 Назад к списку", callback_data=make_callback(user_id, "back_to_products"))],
        [InlineKeyboardButton("🔙 Главное меню", callback_data=make_callback(user_id, "main"))]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def material_detail_keyboard(user_id, material_code):
    """Клавиатура деталей материала с кнопками действий"""
    code_short = material_code[:15]
    
    keyboard = [
        [
            InlineKeyboardButton("✏️ Редактировать", callback_data=make_callback(user_id, "edit_material", code_short)),
            InlineKeyboardButton("🗑️ Удалить", callback_data=make_callback(user_id, "delete_material", code_short))
        ],
        [InlineKeyboardButton("🔙 Назад к списку", callback_data=make_callback(user_id, "back_to_materials"))],
        [InlineKeyboardButton("🔙 Главное меню", callback_data=make_callback(user_id, "main"))]
    ]
    
    return InlineKeyboardMarkup(keyboard)

# ==================== КЛАВИАТУРЫ ДЛЯ РЕДАКТИРОВАНИЯ ====================

def edit_product_fields_keyboard(user_id, product_code):
    """Выбор поля для редактирования изделия/узла"""
    fields = [
        ("📝 Название", "name"),
        ("📂 Категория", "category"),
        ("💰 Цена производства", "price"),
        ("🔢 Кратность", "multiplicity")
    ]
    return edit_field_keyboard(user_id, product_code, fields)

def edit_material_fields_keyboard(user_id, material_code):
    """Выбор поля для редактирования материала"""
    fields = [
        ("📝 Название", "name"),
        ("📂 Категория", "category")
    ]
    return edit_field_keyboard(user_id, material_code, fields)

# ==================== КЛАВИАТУРА ДЛЯ ВЫБОРА ТИПА ====================

def select_type_keyboard(user_id):
    """Выбор типа добавляемого элемента"""
    keyboard = [
        [InlineKeyboardButton("🏗️ Изделие", callback_data=make_callback(user_id, "select_type_product"))],
        [InlineKeyboardButton("🔩 Узел", callback_data=make_callback(user_id, "select_type_node"))],
        [InlineKeyboardButton("⚙️ Материал", callback_data=make_callback(user_id, "select_type_material"))],
        [InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]
    ]
    return InlineKeyboardMarkup(keyboard)
