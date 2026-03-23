"""Expense handler."""

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards import (
    get_cancel_keyboard,
    get_categories_keyboard,
    get_main_menu_keyboard,
    get_skip_cancel_keyboard,
)
from bot.services.finance import create_transaction, get_categories, get_or_create_user, get_user_balance, list_debts
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


def _expense_debt_keyboard(debts: list[dict], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for debt in debts:
        title = debt.get('description') or debt.get('source_name') or 'Debt'
        label = f"🧾 {title} - {debt.get('available_to_spend', 0):.2f} {debt['currency']}"
        builder.button(text=label[:64], callback_data=f"expense_debt_{debt['id']}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text=get_text('btn_cancel', lang), callback_data='cancel'))
    return builder.as_markup()


async def _ask_category(message: Message, state: FSMContext, lang: str):
    categories = await get_categories('expense')
    await state.set_state(ExpenseStates.waiting_for_category)
    prompts = {
        'uz': "Kategoriyani tanlang:",
        'ru': 'Выберите категорию:',
        'en': 'Choose a category:',
    }
    await message.answer(prompts.get(lang, prompts['en']), reply_markup=get_categories_keyboard(categories, row_width=2, lang=lang))


@router.message(Command('expense'))
@router.message(F.text.in_([get_text('btn_add_expense', 'uz'), get_text('btn_add_expense', 'ru'), get_text('btn_add_expense', 'en')]))
async def start_add_expense(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = (user.language_code or 'uz').split('-')[0]
    await state.set_state(ExpenseStates.waiting_for_amount)
    prompt = {
        'uz': "💸 Xarajat qo'shish\n\nSummani kiriting:",
        'ru': '💸 Добавление расхода\n\nВведите сумму:',
        'en': '💸 Add expense\n\nEnter amount:',
    }
    await message.answer(prompt.get(lang, prompt['uz']), reply_markup=get_cancel_keyboard(lang))


@router.message(ExpenseStates.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = (user.language_code or 'uz').split('-')[0]

    try:
        amount = Decimal((message.text or '').replace(',', '.').replace(' ', ''))
    except (AttributeError, InvalidOperation):
        await message.answer(get_text('err_invalid_amount', lang))
        return

    if amount < Decimal(str(MIN_TRANSACTION_AMOUNT)):
        await message.answer(f"❌ Minimal summa: {MIN_TRANSACTION_AMOUNT}")
        return

    balance = await get_user_balance(user.id)
    await state.update_data(amount=str(amount))

    if amount <= Decimal(str(balance['total_balance'])):
        await state.update_data(funding_source='main', debt_id=None)
        await _ask_category(message, state, lang)
        return

    credit_debts = [
        debt for debt in await list_debts(user.id)
        if debt.get('kind') == 'credit_purchase' and Decimal(str(debt.get('available_to_spend', 0))) > 0
    ]
    if not credit_debts:
        text = {
            'uz': f"❌ Asosiy balans yetarli emas. Balans: {balance['total_balance']} {balance['currency']}\nQarz manbasi ham yo'q.",
            'ru': f"❌ Недостаточно основного баланса. Баланс: {balance['total_balance']} {balance['currency']}\nИсточников долга тоже нет.",
            'en': f"❌ Insufficient main balance. Balance: {balance['total_balance']} {balance['currency']}\nNo debt source available either.",
        }
        await message.answer(text.get(lang, text['en']))
        return

    await state.set_state(ExpenseStates.waiting_for_debt_source)
    text = {
        'uz': f"⚠️ Asosiy balans yetarli emas. Balans: {balance['total_balance']} {balance['currency']}\nQarz manbasini tanlang:",
        'ru': f"⚠️ Недостаточно основного баланса. Баланс: {balance['total_balance']} {balance['currency']}\nВыберите источник долга:",
        'en': f"⚠️ Insufficient main balance. Balance: {balance['total_balance']} {balance['currency']}\nSelect a debt source:",
    }
    await message.answer(text.get(lang, text['en']), reply_markup=_expense_debt_keyboard(credit_debts, lang))


@router.callback_query(ExpenseStates.waiting_for_debt_source, F.data.regexp(r'^expense_debt_'))
async def process_expense_debt_source(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    lang = (user.language_code or 'uz').split('-')[0]
    debt_id = callback.data.replace('expense_debt_', '')
    await state.update_data(funding_source='debt', debt_id=debt_id)
    await callback.message.edit_text(
        {
            'uz': "✅ Qarz manbasi tanlandi",
            'ru': '✅ Источник долга выбран',
            'en': '✅ Debt source selected',
        }.get(lang, '✅ Debt source selected')
    )
    await _ask_category(callback.message, state, lang)
    await callback.answer()


@router.callback_query(ExpenseStates.waiting_for_category, F.data.startswith('category_'))
async def process_expense_category(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    lang = (user.language_code or 'uz').split('-')[0]
    category_id = int(callback.data.split('_')[1])
    await state.update_data(category_id=category_id)

    await callback.message.edit_text('✅ Kategoriya tanlandi')
    prompts = {
        'uz': "Izoh kiriting yoki o'tkazib yuboring:",
        'ru': 'Введите описание или пропустите:',
        'en': 'Enter description or skip:',
    }
    await callback.message.answer(prompts.get(lang, prompts['en']), reply_markup=get_skip_cancel_keyboard(lang))
    await state.set_state(ExpenseStates.waiting_for_description)
    await callback.answer()


@router.message(ExpenseStates.waiting_for_description)
async def process_expense_description(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = (user.language_code or 'uz').split('-')[0]

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
        funding_source=data.get('funding_source', 'main'),
        debt_id=data.get('debt_id'),
    )
    balance = await get_user_balance(user.id)
    await state.clear()

    done = {
        'uz': "✅ Xarajat qo'shildi",
        'ru': '✅ Расход добавлен',
        'en': '✅ Expense added',
    }
    await message.answer(
        f"{done.get(lang, done['en'])}\n\n💸 {tx.amount} {tx.currency}\n\n💵 Balans: {balance['total_balance']} {balance['currency']}",
        reply_markup=get_main_menu_keyboard(lang, settings.MINIAPP_URL or None),
    )


@router.callback_query(F.data == 'cancel')
async def cancel_expense(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    lang = (user.language_code or 'uz').split('-')[0]
    await state.clear()
    await callback.message.edit_text(get_text('msg_operation_cancelled', lang))
    await callback.message.answer(
        get_text('msg_main_menu', lang),
        reply_markup=get_main_menu_keyboard(lang, settings.MINIAPP_URL or None),
    )
    await callback.answer()
