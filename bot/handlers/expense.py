"""Expense handler."""

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    get_cancel_keyboard,
    get_categories_keyboard,
    get_main_menu_keyboard,
    get_skip_cancel_keyboard,
)
from bot.services.finance import create_transaction, get_categories, get_or_create_user, get_user_balance
from bot.states import ExpenseStates
from config.constants import MAX_DESCRIPTION_LENGTH, MIN_TRANSACTION_AMOUNT
from config.i18n import get_text
from config.settings import settings

router = Router()


async def _load_user(message_or_callback):
    src = message_or_callback.from_user
    return await get_or_create_user(
        telegram_id=src.id,
        username=src.username,
        first_name=src.first_name,
        last_name=src.last_name,
        language_code=src.language_code,
    )


@router.message(Command('expense'))
@router.message(F.text.in_([get_text('btn_add_expense', 'uz'), get_text('btn_add_expense', 'ru'), get_text('btn_add_expense', 'en')]))
async def start_add_expense(message: Message, state: FSMContext):
    user = await _load_user(message)
    await state.set_state(ExpenseStates.waiting_for_amount)
    prompt = {
        'uz': "💸 Xarajat qo'shish\n\nSummani kiriting:",
        'ru': '💸 Добавление расхода\n\nВведите сумму:',
        'en': '💸 Add expense\n\nEnter amount:',
    }
    await message.answer(prompt.get(user.language_code, prompt['uz']), reply_markup=get_cancel_keyboard(user.language_code))


@router.message(ExpenseStates.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext):
    user = await _load_user(message)

    try:
        amount = Decimal(message.text.replace(',', '.').replace(' ', ''))
    except (AttributeError, InvalidOperation):
        await message.answer("❌ Noto'g'ri summa")
        return

    if amount < Decimal(str(MIN_TRANSACTION_AMOUNT)):
        await message.answer(f"❌ Minimal summa: {MIN_TRANSACTION_AMOUNT}")
        return

    balance = await get_user_balance(user.id)
    if amount > Decimal(str(balance['total_balance'])):
        await message.answer(
            f"❌ Mablag' yetarli emas. Balans: {balance['total_balance']} {balance['currency']}"
        )
        return

    await state.update_data(amount=str(amount))
    categories = await get_categories('expense')

    await state.set_state(ExpenseStates.waiting_for_category)
    await message.answer(
        f"✅ {amount} {user.default_currency}\n\nKategoriyani tanlang:",
        reply_markup=get_categories_keyboard(categories, row_width=2, lang=user.language_code),
    )


@router.callback_query(ExpenseStates.waiting_for_category, F.data.startswith('category_'))
async def process_expense_category(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    category_id = int(callback.data.split('_')[1])
    await state.update_data(category_id=category_id)

    await callback.message.edit_text('✅ Kategoriya tanlandi')
    await callback.message.answer(
        "Izoh kiriting yoki o'tkazib yuboring:",
        reply_markup=get_skip_cancel_keyboard(user.language_code),
    )
    await state.set_state(ExpenseStates.waiting_for_description)
    await callback.answer()


@router.message(ExpenseStates.waiting_for_description)
async def process_expense_description(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = user.language_code

    description = None if message.text == get_text('btn_skip', lang) else message.text
    if description and len(description) > MAX_DESCRIPTION_LENGTH:
        await message.answer(f"❌ Izoh juda uzun (max {MAX_DESCRIPTION_LENGTH})")
        return

    data = await state.get_data()
    tx = await create_transaction(
        user_id=user.id,
        tx_type='expense',
        amount=Decimal(data['amount']),
        category_id=data.get('category_id'),
        description=description,
        currency=user.default_currency,
    )
    balance = await get_user_balance(user.id)
    await state.clear()

    await message.answer(
        f"✅ Xarajat qo'shildi\n\n💸 {tx.amount} {tx.currency}\n\n💵 Balans: {balance['total_balance']} {balance['currency']}",
        reply_markup=get_main_menu_keyboard(lang, settings.MINIAPP_URL or None),
    )


@router.callback_query(F.data == 'cancel')
async def cancel_expense(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    await state.clear()
    await callback.message.edit_text(get_text('msg_operation_cancelled', user.language_code))
    await callback.message.answer(
        get_text('msg_main_menu', user.language_code),
        reply_markup=get_main_menu_keyboard(user.language_code, settings.MINIAPP_URL or None),
    )
    await callback.answer()
