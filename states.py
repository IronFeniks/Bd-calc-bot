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
    
    # Узлы - ДОБАВЛЕНЫ НЕДОСТАЮЩИЕ СОСТОЯНИЯ
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
