from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.finance import create_debt, get_or_create_user, list_debts, pay_debt
from config.i18n import get_text

router = Router()


class DebtStates(StatesGroup):
    waiting_pay_amount = State()
    waiting_add_amount = State()
    waiting_add_description = State()


def _normalize_lang(value: str | None) -> str:
    lang = (value or 'uz').lower()
    if lang.startswith('ru'):
        return 'ru'
    if lang.startswith('en'):
        return 'en'
    return 'uz'


def _render_debts(debts: list[dict], lang: str) -> str:
    if not debts:
        return {'uz': "Qarz yo'q", 'ru': 'Долгов нет', 'en': 'No debts'}[lang]
    lines: list[str] = []
    for debt in debts:
        status = '✅' if debt['remaining'] <= 0 else '⏳'
        created = debt.get('created_at', '')[:16].replace('T', ' ')
        paid_line = ''
        if debt.get('paid_at'):
            paid_text = {'uz': "To'langan", 'ru': 'Погашен', 'en': 'Paid'}.get(lang, 'Paid')
            paid_line = f"{paid_text}: {debt['paid_at'][:16].replace('T',' ')}"
        remaining_label = {'uz': "Qoldiq", 'ru': 'Остаток', 'en': 'Remaining'}.get(lang, 'Remaining')
        lines.append(
            f"{status} <b>{debt['description'] or 'Debt'}</b>\n"
            f"{created}\n"
            f"{remaining_label}: {debt['remaining']:.2f} {debt['currency']} / {debt['amount']:.2f}"
        )
        if paid_line:
            lines.append(paid_line)
        lines.append('')
    return '\n'.join(lines)


def _debts_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text={'uz': "💸 Qarz to'lash", 'ru': '💸 Погасить долг', 'en': '💸 Pay debt'}.get(lang, 'Pay debt'),
            callback_data='debt_pay_list',
        )
    )
    builder.row(
        InlineKeyboardButton(
            text={'uz': '➕ Qarz qo‘shish', 'ru': '➕ Добавить долг', 'en': '➕ Add debt'}.get(lang, 'Add debt'),
            callback_data='debt_add',
        )
    )
    builder.row(
        InlineKeyboardButton(
            text={'uz': '🔄 Yangilash', 'ru': '🔄 Обновить', 'en': '🔄 Refresh'}.get(lang, 'Refresh'),
            callback_data='debt_refresh',
        )
    )
    return builder.as_markup()


def _pay_list_keyboard(debts: list[dict], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for debt in debts:
        if debt['remaining'] <= 0:
            continue
        label = f"{debt['description'] or 'Debt'} • {debt['remaining']:.2f} {debt['currency']}"
        builder.button(text=label[:64], callback_data=f"pay_select_{debt['id']}")
    if debts:
        builder.adjust(1)
    builder.row(
        InlineKeyboardButton(
            text={'uz': '◀️ Orqaga', 'ru': '◀️ Назад', 'en': '◀️ Back'}.get(lang, 'Back'),
            callback_data='debt_back',
        )
    )
    return builder.as_markup()


@router.message(Command('debts'))
@router.message(F.text.in_([get_text('btn_debts', 'uz'), get_text('btn_debts', 'ru'), get_text('btn_debts', 'en')]))
async def cmd_debts(message: Message):
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
    )
    lang = _normalize_lang(user.language_code)
    debts = await list_debts(user.id)
    await message.answer(
        _render_debts(debts, lang),
        parse_mode='HTML',
        reply_markup=_debts_keyboard(lang),
    )


@router.callback_query(F.data == 'debt_refresh')
async def callback_debt_refresh(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        language_code=callback.from_user.language_code,
    )
    lang = _normalize_lang(user.language_code)
    debts = await list_debts(user.id)
    await callback.message.edit_text(
        _render_debts(debts, lang),
        parse_mode='HTML',
        reply_markup=_debts_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == 'debt_pay_list')
async def callback_pay_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        language_code=callback.from_user.language_code,
    )
    lang = _normalize_lang(user.language_code)
    debts = [d for d in await list_debts(user.id) if d['remaining'] > 0]
    if not debts:
        await callback.answer(
            {'uz': "Ochiq qarz yo'q", 'ru': 'Нет открытых долгов', 'en': 'No open debts'}.get(lang, 'No open debts'),
            show_alert=True,
        )
        return
    await callback.message.answer(
        {'uz': "Qaysi qarzni to'laysiz?", 'ru': 'Какой долг погасить?', 'en': 'Select a debt to pay'}.get(lang, 'Select debt'),
        reply_markup=_pay_list_keyboard(debts, lang),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r'^pay_select_'))
async def callback_pay_select(callback: CallbackQuery, state: FSMContext):
    debt_id = callback.data.replace('pay_select_', '')
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        language_code=callback.from_user.language_code,
    )
    lang = _normalize_lang(user.language_code)
    debts = await list_debts(user.id)
    target = next((d for d in debts if d['id'] == debt_id), None)
    if not target:
        await callback.answer({'uz': 'Qarz topilmadi', 'ru': 'Долг не найден', 'en': 'Debt not found'}.get(lang, 'Not found'), show_alert=True)
        return

    await state.set_state(DebtStates.waiting_pay_amount)
    await state.update_data(debt_id=debt_id, debt_currency=target['currency'])

    msg = get_text('msg_debt_pay_prompt', lang).format(currency=target['currency'])
    remaining_line = {
        'uz': f"Qoldiq: {target['remaining']:.2f} {target['currency']}",
        'ru': f"Остаток: {target['remaining']:.2f} {target['currency']}",
        'en': f"Remaining: {target['remaining']:.2f} {target['currency']}",
    }.get(lang, '')
    note = {
        'uz': "Qisman to'lash mumkin",
        'ru': 'Можно частично погашать',
        'en': 'Partial payment allowed',
    }.get(lang, '')
    if remaining_line:
        msg = f"{msg}\n{remaining_line}"
    if note:
        msg = f"{msg}\n{note}"

    await callback.message.answer(msg)
    await callback.answer()


@router.message(DebtStates.waiting_pay_amount)
async def process_debt_payment(message: Message, state: FSMContext):
    data = await state.get_data()
    debt_id = data.get('debt_id')
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
    )
    lang = _normalize_lang(user.language_code)

    parts = (message.text or '').split()
    try:
        amount = Decimal(parts[0].replace(',', '.'))
    except (InvalidOperation, IndexError):
        await message.answer(get_text('err_invalid_amount', lang))
        return

    currency = data.get('debt_currency') or user.default_currency

    try:
        debt = await pay_debt(user.id, debt_id, amount, currency)
    except Exception as exc:
        await state.clear()
        await message.answer(str(exc))
        return

    await state.clear()
    done = {'uz': 'Qarz to\'landi', 'ru': 'Долг погашен', 'en': 'Debt paid'}
    await message.answer(
        f"✅ {done.get(lang, done['en'])}: qoldiq {debt['remaining']:.2f} {debt['currency']}",
        parse_mode='HTML',
    )

    debts = await list_debts(user.id)
    await message.answer(
        _render_debts(debts, lang),
        parse_mode='HTML',
        reply_markup=_debts_keyboard(lang),
    )


@router.message(Command('debt_add'))
async def cmd_debt_add(message: Message):
    parts = (message.text or '').split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Usage: /debt_add <amount> [description]")
        return
    try:
        amount = Decimal(parts[1].replace(',', '.'))
    except InvalidOperation:
        await message.answer("Invalid amount")
        return

    description = parts[2] if len(parts) > 2 else None
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
    )
    lang = _normalize_lang(user.language_code)
    try:
        debt = await create_debt(user.id, amount, user.default_currency, description)
    except Exception as exc:
        await message.answer(str(exc))
        return

    done = {'uz': 'Qarz qo\'shildi', 'ru': 'Долг добавлен', 'en': 'Debt added'}
    await message.answer(f"✅ {done.get(lang, done['en'])}: {debt['amount']:.2f} {debt['currency']}")


@router.callback_query(F.data == 'debt_add')
async def callback_add_debt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DebtStates.waiting_add_amount)
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        language_code=callback.from_user.language_code,
    )
    lang = _normalize_lang(user.language_code)
    prompt = get_text('msg_debt_enter_amount', lang).format(currency=user.default_currency)
    await callback.message.answer(prompt)
    await callback.answer()


@router.message(DebtStates.waiting_add_amount)
async def process_add_amount(message: Message, state: FSMContext):
    parts = (message.text or '').split()
    try:
        amount = Decimal(parts[0].replace(',', '.'))
    except (InvalidOperation, IndexError):
        lang = _normalize_lang(message.from_user.language_code)
        await message.answer(get_text('err_invalid_amount', lang))
        return
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
    )
    currency = user.default_currency
    if len(parts) > 1 and parts[1].upper() in {'UZS', 'USD'}:
        currency = parts[1].upper()
    await state.update_data(add_amount=amount, add_currency=currency)
    await state.set_state(DebtStates.waiting_add_description)
    await message.answer(get_text('msg_debt_enter_description', _normalize_lang(user.language_code)))


@router.message(DebtStates.waiting_add_description)
async def process_add_description(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get('add_amount')
    currency = data.get('add_currency', 'UZS')
    description = (message.text or '').strip() or None

    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
    )
    lang = _normalize_lang(user.language_code)
    try:
        await create_debt(user.id, amount, currency, description)
    except Exception as exc:
        await state.clear()
        await message.answer(str(exc))
        return

    await state.clear()
    ok = get_text('msg_debt_added', lang)
    await message.answer(ok)

    debts = await list_debts(user.id)
    await message.answer(
        _render_debts(debts, lang),
        parse_mode='HTML',
        reply_markup=_debts_keyboard(lang),
    )
