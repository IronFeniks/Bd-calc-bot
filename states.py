from telegram.ext import ContextTypes

# Класс для хранения состояний FSM (Finite State Machine)
class AdminStates:
    """Класс с константами состояний для бота-администратора"""
    
    # Главное меню
    MAIN_MENU = 0
    
    # Состояния для категорий
    CATEGORY_LIST = 1
    CATEGORY_ADD_NAME = 2
    CATEGORY_EDIT_NAME = 3
    CATEGORY_DELETE_CONFIRM = 4
    
    # Состояния для изделий
    PRODUCT_LIST = 10
    PRODUCT_ADD_CODE = 11
    PRODUCT_ADD_NAME = 12
    PRODUCT_ADD_CATEGORY = 13
    PRODUCT_ADD_PRICE = 14
    PRODUCT_ADD_MULTIPLICITY = 15
    PRODUCT_EDIT_SELECT = 16
    PRODUCT_EDIT_FIELD = 17
    PRODUCT_LINK_NODE_SELECT = 18
    PRODUCT_LINK_NODE_QUANTITY = 19
    PRODUCT_LINK_MATERIAL_SELECT = 20
    PRODUCT_LINK_MATERIAL_QUANTITY = 21
    
    # Состояния для узлов
    NODE_LIST = 30
    NODE_ADD_CODE = 31
    NODE_ADD_NAME = 32
    NODE_ADD_CATEGORY = 33
    NODE_ADD_PRICE = 34
    NODE_ADD_MULTIPLICITY = 35
    NODE_EDIT_SELECT = 36
    NODE_EDIT_FIELD = 37
    NODE_LINK_MATERIAL_SELECT = 38
    NODE_LINK_MATERIAL_QUANTITY = 39
    
    # Состояния для материалов
    MATERIAL_LIST = 50
    MATERIAL_ADD_CODE = 51
    MATERIAL_ADD_NAME = 52
    MATERIAL_ADD_CATEGORY = 53
    MATERIAL_EDIT_SELECT = 54
    MATERIAL_EDIT_FIELD = 55
    
    # Состояния для подтверждения
    CONFIRM_ACTION = 90
    WAITING_FOR_AUTH_CODE = 91  # для авторизации Google

# Вспомогательная функция для получения данных пользователя
def get_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> dict:
    """Получает или создаёт словарь данных для пользователя"""
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    return context.chat_data['user_data'][user_id]

def set_user_state(context: ContextTypes.DEFAULT_TYPE, user_id: int, state: int):
    """Устанавливает состояние для пользователя"""
    user_data = get_user_data(context, user_id)
    user_data['state'] = state

def get_user_state(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> int:
    """Возвращает состояние пользователя"""
    user_data = get_user_data(context, user_id)
    return user_data.get('state', AdminStates.MAIN_MENU)

def clear_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Очищает данные пользователя"""
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        del context.chat_data['user_data'][user_id]
