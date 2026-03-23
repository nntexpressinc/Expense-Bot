"""
FSM States for bot conversations
"""
from aiogram.fsm.state import State, StatesGroup


class IncomeStates(StatesGroup):
    """States for adding income"""
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()


class ExpenseStates(StatesGroup):
    """States for adding expense"""
    waiting_for_amount = State()
    waiting_for_debt_source = State()
    waiting_for_category = State()
    waiting_for_description = State()


class TransferStates(StatesGroup):
    """States for creating transfer"""
    waiting_for_recipient = State()
    waiting_for_amount = State()
    waiting_for_description = State()
    waiting_for_confirmation = State()


class SpendTransferStates(StatesGroup):
    """States for spending from transfer"""
    waiting_for_transfer_selection = State()
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()


class ReportStates(StatesGroup):
    """States for generating reports"""
    waiting_for_period = State()
    waiting_for_format = State()
    waiting_for_custom_dates = State()


class SettingsStates(StatesGroup):
    """States for settings"""
    waiting_for_currency = State()
    waiting_for_language = State()


class CategoryStates(StatesGroup):
    """States for managing categories"""
    waiting_for_category_name = State()
    waiting_for_category_type = State()
    waiting_for_category_icon = State()
