from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard(user_id):
    """Главное меню"""
    keyboard = [
        [
            InlineKeyboardButton("📋 Категории", callback_data=f"user_{user_id}_categories"),
            InlineKeyboardButton("🏗️ Изделия", callback_data=f"user_{user_id}_products")
        ],
        [
            InlineKeyboardButton("🔩 Узлы", callback_data=f"user_{user_id}_nodes"),
            InlineKeyboardButton("⚙️ Материалы", callback_data=f"user_{user_id}_materials")
        ],
        [InlineKeyboardButton("❌ Завершить", callback_data=f"user_{user_id}_exit")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button(user_id, action="main"):
    """Кнопка назад"""
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"user_{user_id}_back_to_{action}")]]
    return InlineKeyboardMarkup(keyboard)

def cancel_button(user_id):
    """Кнопка отмены"""
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"user_{user_id}_cancel")]]
    return InlineKeyboardMarkup(keyboard)

def categories_keyboard(categories, user_id, page=1, total_pages=1):
    """Клавиатура со списком категорий"""
    keyboard = []
    
    for cat in categories:
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"user_{user_id}_cat_{cat}")])
    
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"user_{user_id}_categories_page_{page-1}"))
    
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"user_{user_id}_categories_page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("➕ Добавить категорию", callback_data=f"user_{user_id}_add_category")])
    keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data=f"user_{user_id}_back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

def products_keyboard(products, user_id, page=1, total_pages=1, category=None):
    """Клавиатура со списком изделий"""
    keyboard = []
    
    for p in products:
        text = f"{p['code']} - {p['name']}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"user_{user_id}_product_{p['code']}")])
    
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"user_{user_id}_products_page_{page-1}"))
    
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"user_{user_id}_products_page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("➕ Добавить изделие", callback_data=f"user_{user_id}_add_product")])
    
    if category:
        keyboard.append([InlineKeyboardButton("🔙 К категориям", callback_data=f"user_{user_id}_back_to_categories")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data=f"user_{user_id}_back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

def materials_keyboard(materials, user_id, page=1, total_pages=1):
    """Клавиатура со списком материалов"""
    keyboard = []
    
    for m in materials:
        text = f"{m['code']} - {m['name']}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"user_{user_id}_material_{m['code']}")])
    
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"user_{user_id}_materials_page_{page-1}"))
    
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"user_{user_id}_materials_page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("➕ Добавить материал", callback_data=f"user_{user_id}_add_material")])
    keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data=f"user_{user_id}_back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

def product_detail_keyboard(user_id, product_code):
    """Клавиатура для детального просмотра изделия"""
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"user_{user_id}_edit_{product_code}")],
        [InlineKeyboardButton("🔗 Привязать узел", callback_data=f"user_{user_id}_link_node_{product_code}")],
        [InlineKeyboardButton("⚙️ Привязать материал", callback_data=f"user_{user_id}_link_material_{product_code}")],
        [InlineKeyboardButton("🔙 К списку", callback_data=f"user_{user_id}_back_to_products")]
    ]
    return InlineKeyboardMarkup(keyboard)

def material_detail_keyboard(user_id, material_code):
    """Клавиатура для детального просмотра материала"""
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"user_{user_id}_edit_material_{material_code}")],
        [InlineKeyboardButton("🔙 К списку", callback_data=f"user_{user_id}_back_to_materials")]
    ]
    return InlineKeyboardMarkup(keyboard)

def noop_keyboard():
    """Пустая клавиатура (заглушка)"""
    keyboard = [[InlineKeyboardButton("⏳ Загрузка...", callback_data="noop")]]
    return InlineKeyboardMarkup(keyboard)
