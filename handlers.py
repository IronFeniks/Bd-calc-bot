import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import ADMIN_ID, ITEMS_PER_PAGE
from keyboards import (
    main_menu_keyboard, categories_keyboard, products_keyboard,
    materials_keyboard, product_detail_keyboard, material_detail_keyboard,
    cancel_button, back_button, noop_keyboard
)
from excel_handler import ExcelHandler
from states import AdminStates, get_user_data, set_user_state, get_user_state, clear_user_data
from drive_client import GoogleDriveClient

logger = logging.getLogger(__name__)

# Глобальный обработчик Excel
excel_handler = None

def set_excel_handler(handler: ExcelHandler):
    global excel_handler
    excel_handler = handler

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа к этому боту.")
        return False
    return True

async def check_admin_callback(query, user_id) -> bool:
    if user_id != ADMIN_ID:
        await query.answer("⛔ У вас нет доступа к этому боту", show_alert=True)
        return False
    return True

async def check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    global excel_handler
    if not excel_handler.drive_client.creds:
        await start_auth(update, context)
        return False
    return True

async def check_auth_callback(query, context, user_id) -> bool:
    global excel_handler
    if not excel_handler.drive_client.creds:
        await query.edit_message_text("🔑 Требуется авторизация. Используйте /start")
        return False
    return True

async def load_data(update, context, user_id) -> bool:
    success, message = await excel_handler.download_and_load_async()
    if not success:
        await update.message.reply_text(message)
        return False
    return True

async def load_data_callback(query, context, user_id) -> bool:
    success, message = await excel_handler.download_and_load_async()
    if not success:
        await query.edit_message_text(message)
        return False
    return True

# ==================== АВТОРИЗАЦИЯ ====================

async def start_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    drive_client = GoogleDriveClient()
    auth_url, flow = drive_client.get_auth_url()
    
    user_data = get_user_data(context, update.effective_user.id)
    user_data['auth_flow'] = flow
    set_user_state(context, update.effective_user.id, AdminStates.WAITING_FOR_AUTH_CODE)
    
    text = (
        "🔑 Требуется авторизация в Google Drive\n\n"
        "1. Перейдите по ссылке:\n"
        f"{auth_url}\n\n"
        "2. Войдите в свой Google аккаунт\n"
        "3. Нажмите 'Разрешить'\n"
        "4. Скопируйте полученный код\n\n"
        "5. Введите код в ответном сообщении:"
    )
    
    await update.message.reply_text(text)

# ==================== ГЛАВНОЕ МЕНЮ ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    user_id = update.effective_user.id
    clear_user_data(context, user_id)
    set_user_state(context, user_id, AdminStates.MAIN_MENU)
    
    if not excel_handler.drive_client.creds:
        await start_auth(update, context)
        return
    
    text = (
        "🏭 УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ\n\n"
        "Выберите раздел для работы:"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(user_id)
    )

async def back_to_main(query, context, user_id):
    clear_user_data(context, user_id)
    set_user_state(context, user_id, AdminStates.MAIN_MENU)
    
    text = (
        "🏭 УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ\n\n"
        "Выберите раздел для работы:"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== КАТЕГОРИИ ====================

async def show_categories(query, context, user_id, page=1):
    if not await check_auth_callback(query, context, user_id):
        return
    
    success = await load_data_callback(query, context, user_id)
    if not success:
        return
    
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
    set_user_state(context, user_id, AdminStates.CATEGORY_ADD_NAME)
    
    await query.edit_message_text(
        "✏️ Добавление новой категории\n\n"
        "Введите название категории:",
        reply_markup=cancel_button(user_id)
    )

async def add_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    
    if not text or len(text) < 2:
        await update.message.reply_text(
            "❌ Название должно содержать минимум 2 символа. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    await update.message.reply_text(
        f"✅ Категория '{text}' будет доступна при создании элементов",
        reply_markup=back_button(user_id, "categories")
    )
# ==================== ИЗДЕЛИЯ ====================

async def show_products(query, context, user_id, category=None, page=1):
    if not await check_auth_callback(query, context, user_id):
        return
    
    success = await load_data_callback(query, context, user_id)
    if not success:
        return
    
    if category == "Все" or not category:
        mask = excel_handler.df_nomenclature['Тип'].str.lower().isin(['изделие', 'узел'])
        filtered = excel_handler.df_nomenclature[mask]
        total_items = len(filtered)
        items = []
        
        start = (page - 1) * ITEMS_PER_PAGE
        end = min(start + ITEMS_PER_PAGE, total_items)
        
        for idx, row in filtered.iloc[start:end].iterrows():
            items.append({
                'code': row['Код'],
                'name': row['Наименование']
            })
    else:
        items, total_items = excel_handler.get_products_by_category(category, page-1, ITEMS_PER_PAGE)
    
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    user_data = get_user_data(context, user_id)
    user_data['current_category'] = category
    
    set_user_state(context, user_id, AdminStates.PRODUCT_LIST)
    
    await query.edit_message_text(
        f"🏗️ ИЗДЕЛИЯ\n\nСтраница {page} из {total_pages}",
        reply_markup=products_keyboard(items, user_id, page, total_pages, category)
    )

async def show_product_detail(query, context, user_id, product_code):
    if not await check_auth_callback(query, context, user_id):
        return
    
    success = await load_data_callback(query, context, user_id)
    if not success:
        return
    
    product = excel_handler.get_product_by_code(product_code)
    if not product:
        await query.edit_message_text("❌ Изделие не найдено")
        return
    
    user_data = get_user_data(context, user_id)
    user_data['current_product'] = product_code
    
    nodes = []
    materials = []
    
    specs = excel_handler.df_specifications[
        excel_handler.df_specifications['Родитель'] == product_code
    ]
    
    for _, spec in specs.iterrows():
        child_code = spec['Потомок']
        quantity = spec['Количество']
        
        child_row = excel_handler.df_nomenclature[
            excel_handler.df_nomenclature['Код'] == child_code
        ]
        
        if len(child_row) > 0:
            child_type = child_row.iloc[0]['Тип'].lower()
            child_name = child_row.iloc[0]['Наименование']
            
            if 'узел' in child_type:
                nodes.append(f"• {child_name} ({quantity} шт)")
            elif 'материал' in child_type:
                materials.append(f"• {child_name} ({quantity} шт)")
    
    text = f"🏗️ Изделие: {product['Наименование']}\n\n"
    text += f"Код: {product['Код']}\n"
    text += f"Категория: {product.get('Категории', 'не указана')}\n"
    text += f"Цена производства: {product.get('Цена производства', '0 ISK')}\n"
    text += f"Кратность: {product.get('Кратность', 1)}\n\n"
    
    if nodes:
        text += "🔩 Узлы в составе:\n" + "\n".join(nodes) + "\n\n"
    else:
        text += "🔩 Узлы в составе: нет\n\n"
    
    if materials:
        text += "⚙️ Материалы в составе:\n" + "\n".join(materials) + "\n"
    else:
        text += "⚙️ Материалы в составе: нет\n"
    
    await query.edit_message_text(
        text,
        reply_markup=product_detail_keyboard(user_id, product_code)
    )

async def add_product_start(query, context, user_id):
    user_data = get_user_data(context, user_id)
    user_data['new_product'] = {}
    set_user_state(context, user_id, AdminStates.PRODUCT_ADD_CODE)
    
    await query.edit_message_text(
        "✏️ Добавление нового изделия\n\n"
        "Шаг 1 из 5: Введите код изделия\n"
        "(например: `изд. 010`)",
        reply_markup=cancel_button(user_id)
    )

async def add_product_code(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    if not text or len(text) < 3:
        await update.message.reply_text(
            "❌ Код должен содержать минимум 3 символа. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    if text in excel_handler.df_nomenclature['Код'].values:
        await update.message.reply_text(
            f"❌ Код '{text}' уже существует. Введите другой код:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    user_data['new_product']['code'] = text
    set_user_state(context, user_id, AdminStates.PRODUCT_ADD_NAME)
    
    await update.message.reply_text(
        "Шаг 2 из 5: Введите название изделия",
        reply_markup=cancel_button(user_id)
    )

async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    if not text or len(text) < 2:
        await update.message.reply_text(
            "❌ Название должно содержать минимум 2 символа. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    user_data['new_product']['name'] = text
    
    categories = excel_handler.get_unique_categories()
    
    if not categories:
        user_data['new_product']['category'] = ''
        set_user_state(context, user_id, AdminStates.PRODUCT_ADD_PRICE)
        await update.message.reply_text(
            "Шаг 3 из 5: Введите цену производства (например: `5400000000 ISK`)",
            reply_markup=cancel_button(user_id)
        )
        return
    
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"user_{user_id}_select_cat_{cat}")])
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data=f"user_{user_id}_select_cat_skip")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"user_{user_id}_cancel")])
    
    await update.message.reply_text(
        "Шаг 3 из 5: Выберите категорию",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_category_callback(query, context, user_id, category):
    user_data = get_user_data(context, user_id)
    
    if category == "skip":
        user_data['new_product']['category'] = ''
    else:
        user_data['new_product']['category'] = category
    
    set_user_state(context, user_id, AdminStates.PRODUCT_ADD_PRICE)
    
    await query.edit_message_text(
        "Шаг 4 из 5: Введите цену производства\n"
        "(например: `5400000000 ISK`)",
        reply_markup=cancel_button(user_id)
    )

async def add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    user_data['new_product']['price'] = text
    set_user_state(context, user_id, AdminStates.PRODUCT_ADD_MULTIPLICITY)
    
    await update.message.reply_text(
        "Шаг 5 из 5: Введите кратность (целое число, например: 10)",
        reply_markup=cancel_button(user_id)
    )

async def add_product_multiplicity(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    try:
        multiplicity = int(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Кратность должна быть целым числом. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    new_product = user_data['new_product']
    
    success, message = excel_handler.add_product(
        code=new_product['code'],
        name=new_product['name'],
        type_name='изделие',
        category=new_product.get('category', ''),
        price=new_product.get('price', '0 ISK'),
        multiplicity=multiplicity
    )
    
    if success:
        save_success, save_message = await excel_handler.save_and_upload_async()
        if save_success:
            await update.message.reply_text(
                f"{message}\n\n✅ Изменения сохранены в файл",
                reply_markup=back_button(user_id, "products")
            )
        else:
            await update.message.reply_text(
                f"{message}\n\n❌ Ошибка сохранения: {save_message}",
                reply_markup=back_button(user_id, "products")
            )
    else:
        await update.message.reply_text(
            message,
            reply_markup=cancel_button(user_id)
        )
    
    clear_user_data(context, user_id)
# ==================== МАТЕРИАЛЫ ====================

async def show_materials(query, context, user_id, page=1):
    if not await check_auth_callback(query, context, user_id):
        return
    
    success = await load_data_callback(query, context, user_id)
    if not success:
        return
    
    materials, total_items = excel_handler.get_materials(page-1, ITEMS_PER_PAGE)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    set_user_state(context, user_id, AdminStates.MATERIAL_LIST)
    
    await query.edit_message_text(
        f"⚙️ МАТЕРИАЛЫ\n\nСтраница {page} из {total_pages}",
        reply_markup=materials_keyboard(materials, user_id, page, total_pages)
    )

async def show_material_detail(query, context, user_id, material_code):
    if not await check_auth_callback(query, context, user_id):
        return
    
    success = await load_data_callback(query, context, user_id)
    if not success:
        return
    
    material = excel_handler.get_product_by_code(material_code)
    if not material:
        await query.edit_message_text("❌ Материал не найден")
        return
    
    used_in = excel_handler.df_specifications[
        excel_handler.df_specifications['Потомок'] == material_code
    ]
    
    text = f"⚙️ Материал: {material['Наименование']}\n\n"
    text += f"Код: {material['Код']}\n"
    text += f"Категория: {material.get('Категории', 'не указана')}\n\n"
    
    if len(used_in) > 0:
        text += "Используется в:\n"
        for _, spec in used_in.iterrows():
            parent_code = spec['Родитель']
            quantity = spec['Количество']
            
            parent = excel_handler.get_product_by_code(parent_code)
            if parent:
                text += f"• {parent['Наименование']} ({quantity} шт)\n"
    else:
        text += "Используется в: нигде"
    
    await query.edit_message_text(
        text,
        reply_markup=material_detail_keyboard(user_id, material_code)
    )

async def add_material_start(query, context, user_id):
    user_data = get_user_data(context, user_id)
    user_data['new_material'] = {}
    set_user_state(context, user_id, AdminStates.MATERIAL_ADD_CODE)
    
    await query.edit_message_text(
        "✏️ Добавление нового материала\n\n"
        "Шаг 1 из 3: Введите код материала\n"
        "(например: `мат 030`)",
        reply_markup=cancel_button(user_id)
    )

async def add_material_code(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    if not text or len(text) < 3:
        await update.message.reply_text(
            "❌ Код должен содержать минимум 3 символа. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    if text in excel_handler.df_nomenclature['Код'].values:
        await update.message.reply_text(
            f"❌ Код '{text}' уже существует. Введите другой код:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    user_data['new_material']['code'] = text
    set_user_state(context, user_id, AdminStates.MATERIAL_ADD_NAME)
    
    await update.message.reply_text(
        "Шаг 2 из 3: Введите название материала",
        reply_markup=cancel_button(user_id)
    )

async def add_material_name(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    user_data = get_user_data(context, user_id)
    
    if not text or len(text) < 2:
        await update.message.reply_text(
            "❌ Название должно содержать минимум 2 символа. Попробуйте ещё раз:",
            reply_markup=cancel_button(user_id)
        )
        return
    
    user_data['new_material']['name'] = text
    
    categories = excel_handler.get_unique_categories()
    
    if not categories:
        await save_material(update, context, user_id, '')
        return
    
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"user_{user_id}_select_matcat_{cat}")])
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data=f"user_{user_id}_select_matcat_skip")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"user_{user_id}_cancel")])
    
    set_user_state(context, user_id, AdminStates.MATERIAL_ADD_CATEGORY)
    
    await update.message.reply_text(
        "Шаг 3 из 3: Выберите категорию (необязательно)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_material_category_callback(query, context, user_id, category):
    await save_material(query, context, user_id, category)

async def save_material(update_or_query, context, user_id, category):
    user_data = get_user_data(context, user_id)
    new_material = user_data.get('new_material', {})
    
    success, message = excel_handler.add_material(
        code=new_material['code'],
        name=new_material['name'],
        category=category if category != "skip" else ''
    )
    
    if success:
        save_success, save_message = await excel_handler.save_and_upload_async()
        if save_success:
            await update_or_query.message.reply_text(
                f"{message}\n\n✅ Изменения сохранены в файл",
                reply_markup=back_button(user_id, "materials")
            )
        else:
            await update_or_query.message.reply_text(
                f"{message}\n\n❌ Ошибка сохранения: {save_message}",
                reply_markup=back_button(user_id, "materials")
            )
    else:
        await update_or_query.message.reply_text(
            message,
            reply_markup=cancel_button(user_id)
        )
    
    clear_user_data(context, user_id)

# ==================== ПРИВЯЗКА УЗЛОВ ====================

async def link_node_start(query, context, user_id, product_code):
    user_data = get_user_data(context, user_id)
    user_data['link_product'] = product_code
    set_user_state(context, user_id, AdminStates.PRODUCT_LINK_NODE_SELECT)
    
    mask = excel_handler.df_nomenclature['Тип'].str.lower() == 'узел'
    nodes_df = excel_handler.df_nomenclature[mask]
    
    keyboard = []
    for _, row in nodes_df.iterrows():
        text = f"{row['Код']} - {row['Наименование']}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"user_{user_id}_select_node_{row['Код']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"user_{user_id}_cancel")])
    
    await query.edit_message_text(
        "🔗 Привязка узла к изделию\n\n"
        "Выберите узел из списка:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_node_callback(query, context, user_id, node_code):
    user_data = get_user_data(context, user_id)
    user_data['link_node'] = node_code
    set_user_state(context, user_id, AdminStates.PRODUCT_LINK_NODE_QUANTITY)
    
    await query.edit_message_text(
        "✏️ Введите количество узлов (шт):",
        reply_markup=cancel_button(user_id)
    )

async def link_node_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
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
    
    product_code = user_data.get('link_product')
    node_code = user_data.get('link_node')
    
    success, message = excel_handler.link_node_to_product(product_code, node_code, quantity)
    
    if success:
        save_success, save_message = await excel_handler.save_and_upload_async()
        if save_success:
            await update.message.reply_text(
                f"{message}\n\n✅ Изменения сохранены в файл",
                reply_markup=back_button(user_id, f"product_{product_code}")
            )
        else:
            await update.message.reply_text(
                f"{message}\n\n❌ Ошибка сохранения: {save_message}",
                reply_markup=back_button(user_id, f"product_{product_code}")
            )
    else:
        await update.message.reply_text(
            message,
            reply_markup=cancel_button(user_id)
        )
    
    clear_user_data(context, user_id)

# ==================== ПРИВЯЗКА МАТЕРИАЛОВ ====================

async def link_material_start(query, context, user_id, parent_code, parent_type='product'):
    user_data = get_user_data(context, user_id)
    user_data['link_parent'] = parent_code
    user_data['link_parent_type'] = parent_type
    set_user_state(context, user_id, AdminStates.PRODUCT_LINK_MATERIAL_SELECT)
    
    mask = excel_handler.df_nomenclature['Тип'].str.lower() == 'материал'
    materials_df = excel_handler.df_nomenclature[mask]
    
    keyboard = []
    for _, row in materials_df.iterrows():
        text = f"{row['Код']} - {row['Наименование']}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"user_{user_id}_select_material_{row['Код']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"user_{user_id}_cancel")])
    
    await query.edit_message_text(
        "⚙️ Привязка материала\n\n"
        "Выберите материал из списка:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_material_callback(query, context, user_id, material_code):
    user_data = get_user_data(context, user_id)
    user_data['link_material'] = material_code
    set_user_state(context, user_id, AdminStates.PRODUCT_LINK_MATERIAL_QUANTITY)
    
    await query.edit_message_text(
        "✏️ Введите количество материала (шт):",
        reply_markup=cancel_button(user_id)
    )

async def link_material_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
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
    material_code = user_data.get('link_material')
    
    success, message = excel_handler.link_material_to_product(parent_code, material_code, quantity)
    
    if success:
        save_success, save_message = await excel_handler.save_and_upload_async()
        if save_success:
            await update.message.reply_text(
                f"{message}\n\n✅ Изменения сохранены в файл",
                reply_markup=back_button(user_id, f"product_{parent_code}")
            )
        else:
            await update.message.reply_text(
                f"{message}\n\n❌ Ошибка сохранения: {save_message}",
                reply_markup=back_button(user_id, f"product_{parent_code}")
            )
    else:
        await update.message.reply_text(
            message,
            reply_markup=cancel_button(user_id)
        )
    
    clear_user_data(context, user_id)

# ==================== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"📨 Сообщение от {user_id}: {update.message.text[:50]}...")
    
    user_data = get_user_data(context, user_id)
    state = get_user_state(context, user_id)
    text = update.message.text.strip()
    
    if state == AdminStates.WAITING_FOR_AUTH_CODE:
        flow = user_data.get('auth_flow')
        if not flow:
            await update.message.reply_text("❌ Ошибка: сессия авторизации устарела. Начните заново с /start")
            return
        
        success, message = excel_handler.drive_client.exchange_code(text, flow)
        if success:
            await update.message.reply_text(message)
            await start_command(update, context)
        else:
            await update.message.reply_text(message)
        return
    
    if state == AdminStates.CATEGORY_ADD_NAME:
        await add_category_name(update, context, text)
        return
    
    if state == AdminStates.PRODUCT_ADD_CODE:
        await add_product_code(update, context, text)
        return
    if state == AdminStates.PRODUCT_ADD_NAME:
        await add_product_name(update, context, text)
        return
    if state == AdminStates.PRODUCT_ADD_PRICE:
        await add_product_price(update, context, text)
        return
    if state == AdminStates.PRODUCT_ADD_MULTIPLICITY:
        await add_product_multiplicity(update, context, text)
        return
    
    if state == AdminStates.MATERIAL_ADD_CODE:
        await add_material_code(update, context, text)
        return
    if state == AdminStates.MATERIAL_ADD_NAME:
        await add_material_name(update, context, text)
        return
    
    if state == AdminStates.PRODUCT_LINK_NODE_QUANTITY:
        await link_node_quantity(update, context, text)
        return
    
    if state in [AdminStates.PRODUCT_LINK_MATERIAL_QUANTITY, AdminStates.NODE_LINK_MATERIAL_QUANTITY]:
        await link_material_quantity(update, context, text)
        return
    
    await update.message.reply_text(
        "❓ Я ожидаю команды из меню. Используйте /start",
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== ОБРАБОТЧИК КНОПОК ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if not data.startswith(f"user_{user_id}_") and data not in ["noop"]:
        await query.answer("⛔ Эта кнопка не для вас", show_alert=True)
        return
    
    if not await check_admin_callback(query, user_id):
        return
    
    action = data.replace(f"user_{user_id}_", "")
    
    if action == "main":
        await back_to_main(query, context, user_id)
        return
    
    if action == "exit":
        await query.edit_message_text("👋 До свидания!")
        return
    
    if action == "categories":
        await show_categories(query, context, user_id, 1)
        return
    
    if action.startswith("categories_page_"):
        page = int(action.replace("categories_page_", ""))
        await show_categories(query, context, user_id, page)
        return
    
    if action == "add_category":
        await add_category_start(query, context, user_id)
        return
    
    if action == "products":
        await show_products(query, context, user_id, "Все", 1)
        return
    
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
        product_code = action.replace("product_", "")
        await show_product_detail(query, context, user_id, product_code)
        return
    
    if action.startswith("link_node_"):
        product_code = action.replace("link_node_", "")
        await link_node_start(query, context, user_id, product_code)
        return
    
    if action.startswith("link_material_"):
        product_code = action.replace("link_material_", "")
        await link_material_start(query, context, user_id, product_code, 'product')
        return
    
    if action == "materials":
        await show_materials(query, context, user_id, 1)
        return
    
    if action.startswith("materials_page_"):
        page = int(action.replace("materials_page_", ""))
        await show_materials(query, context, user_id, page)
        return
    
    if action == "add_material":
        await add_material_start(query, context, user_id)
        return
    
    if action.startswith("material_"):
        material_code = action.replace("material_", "")
        await show_material_detail(query, context, user_id, material_code)
        return
    
    if action.startswith("select_cat_"):
        category = action.replace("select_cat_", "")
        await select_category_callback(query, context, user_id, category)
        return
    
    if action.startswith("select_matcat_"):
        category = action.replace("select_matcat_", "")
        await select_material_category_callback(query, context, user_id, category)
        return
    
    if action.startswith("select_node_"):
        node_code = action.replace("select_node_", "")
        await select_node_callback(query, context, user_id, node_code)
        return
    
    if action.startswith("select_material_"):
        material_code = action.replace("select_material_", "")
        await select_material_callback(query, context, user_id, material_code)
        return
    
    if action == "back_to_main":
        await back_to_main(query, context, user_id)
        return
    
    if action == "back_to_categories":
        await show_categories(query, context, user_id, 1)
        return
    
    if action == "back_to_products":
        user_data = get_user_data(context, user_id)
        category = user_data.get('current_category', "Все")
        await show_products(query, context, user_id, category, 1)
        return
    
    if action == "back_to_materials":
        await show_materials(query, context, user_id, 1)
        return
    
    if action.startswith("back_to_product_"):
        product_code = action.replace("back_to_product_", "")
        await show_product_detail(query, context, user_id, product_code)
        return
    
    if action == "cancel":
        clear_user_data(context, user_id)
        set_user_state(context, user_id, AdminStates.MAIN_MENU)
        await query.edit_message_text("❌ Действие отменено")
        return
    
    if action == "noop":
        return
    
    logger.warning(f"Неизвестное действие: {action}")
    await query.edit_message_text("❌ Неизвестная команда")
