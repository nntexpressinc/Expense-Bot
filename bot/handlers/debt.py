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
    waiting_add_amount = State()
    waiting_add_description = State()
    waiting_pay_amount = State()


def _normalize_lang(value: str | None) -> str:
    lang = (value or 'uz').lower()
    if lang.startswith('ru'):
        return 'ru'
    if lang.startswith('en'):
        return 'en'
    return 'uz'


def _debt_kind_label(kind: str | None, lang: str) -> str:
    labels = {
        'cash_loan': {'uz': "Naqd qarz", 'ru': 'Деньги в долг', 'en': 'Cash loan'},
        'credit_purchase': {'uz': 'Qarzga xarid', 'ru': 'Покупка в долг', 'en': 'Buy on credit'},
    }
    return labels.get(kind or 'credit_purchase', labels['credit_purchase']).get(lang, labels['credit_purchase']['en'])


def _parse_amount_and_currency(text: str | None, default_currency: str) -> tuple[Decimal, str]:
    parts = (text or '').split()
    if not parts:
        raise InvalidOperation
    amount = Decimal(parts[0].replace(',', '.'))
    currency = default_currency
    if len(parts) > 1 and parts[1].upper() in {'UZS', 'USD'}:
        currency = parts[1].upper()
    return amount, currency


def _render_debts(debts: list[dict], lang: str) -> str:
    if not debts:
        return {'uz': "Qarz yo'q", 'ru': 'Долгов нет', 'en': 'No debts'}[lang]

    lines: list[str] = []
    for debt in debts:
        status = '✅' if debt['remaining'] <= 0 else '⏳'
        created = debt.get('created_at', '')[:16].replace('T', ' ')
        kind_label = _debt_kind_label(debt.get('kind'), lang)
        title = debt.get('description') or debt.get('source_name') or kind_label
        lines.append(f"{status} <b>{title}</b>")
        lines.append(f"{kind_label} • {created}")
        lines.append(
            {
                'uz': f"Qoldiq: {debt['remaining']:.2f} {debt['currency']} / {debt['amount']:.2f}",
                'ru': f"Остаток: {debt['remaining']:.2f} {debt['currency']} / {debt['amount']:.2f}",
                'en': f"Remaining: {debt['remaining']:.2f} {debt['currency']} / {debt['amount']:.2f}",
            }[lang]
        )
        if debt.get('kind') == 'credit_purchase':
            lines.append(
                {
                    'uz': f"Ishlatish mumkin: {debt.get('available_to_spend', 0):.2f} {debt['currency']}",
                    'ru': f"Доступно для расхода: {debt.get('available_to_spend', 0):.2f} {debt['currency']}",
                    'en': f"Available to spend: {debt.get('available_to_spend', 0):.2f} {debt['currency']}",
                }[lang]
            )
        else:
            lines.append(
                {
                    'uz': "Asosiy balansga tushadi",
                    'ru': 'Попадает в основной баланс',
                    'en': 'Goes to main balance',
                }[lang]
            )
        if debt.get('paid_at'):
            lines.append(
                {
                    'uz': f"To'langan: {debt['paid_at'][:16].replace('T', ' ')}",
                    'ru': f"Погашен: {debt['paid_at'][:16].replace('T', ' ')}",
                    'en': f"Paid: {debt['paid_at'][:16].replace('T', ' ')}",
                }[lang]
            )
        lines.append('')
    return '\n'.join(lines)


def _debts_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text={'uz': "💸 Qarz to'lash", 'ru': '💸 Погасить долг', 'en': '💸 Pay debt'}[lang],
            callback_data='debt_pay_list',
        )
    )
    builder.row(
        InlineKeyboardButton(
            text={'uz': '💵 Naqd qarz', 'ru': '💵 Деньги в долг', 'en': '💵 Borrow cash'}[lang],
            callback_data='debt_add_cash',
        ),
        InlineKeyboardButton(
            text={'uz': '🧾 Qarzga xarid', 'ru': '🧾 Покупка в долг', 'en': '🧾 Buy on credit'}[lang],
            callback_data='debt_add_credit',
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text={'uz': '🔄 Yangilash', 'ru': '🔄 Обновить', 'en': '🔄 Refresh'}[lang],
            callback_data='debt_refresh',
        )
    )
    return builder.as_markup()


def _pay_list_keyboard(debts: list[dict], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for debt in debts:
      if debt['remaining'] <= 0:
          continue
      prefix = '💵' if debt.get('kind') == 'cash_loan' else '🧾'
      title = debt.get('description') or debt.get('source_name') or _debt_kind_label(debt.get('kind'), lang)
      label = f"{prefix} {title} - {debt['remaining']:.2f} {debt['currency']}"
      builder.button(text=label[:64], callback_data=f"pay_select_{debt['id']}")
    if debts:
        builder.adjust(1)
    builder.row(
        InlineKeyboardButton(
            text={'uz': '◀️ Orqaga', 'ru': '◀️ Назад', 'en': '◀️ Back'}[lang],
            callback_data='debt_back',
        )
    )
    return builder.as_markup()


async def _load_user(event: Message | CallbackQuery):
    src = event.from_user
    return await get_or_create_user(
        telegram_id=src.id,
        username=src.username,
        first_name=src.first_name,
        last_name=src.last_name,
        language_code=src.language_code,
    )


@router.message(Command('debts'))
@router.message(F.text.in_([get_text('btn_debts', 'uz'), get_text('btn_debts', 'ru'), get_text('btn_debts', 'en')]))
async def cmd_debts(message: Message):
    user = await _load_user(message)
    lang = _normalize_lang(user.language_code)
    debts = await list_debts(user.id)
    await message.answer(_render_debts(debts, lang), parse_mode='HTML', reply_markup=_debts_keyboard(lang))


@router.callback_query(F.data == 'debt_refresh')
@router.callback_query(F.data == 'debt_back')
async def callback_debt_refresh(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await _load_user(callback)
    lang = _normalize_lang(user.language_code)
    debts = await list_debts(user.id)
    await callback.message.edit_text(_render_debts(debts, lang), parse_mode='HTML', reply_markup=_debts_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data.in_({'debt_add_cash', 'debt_add_credit'}))
async def callback_add_debt(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    lang = _normalize_lang(user.language_code)
    debt_kind = 'cash_loan' if callback.data == 'debt_add_cash' else 'credit_purchase'
    await state.set_state(DebtStates.waiting_add_amount)
    await state.update_data(add_kind=debt_kind)
    hint = {
        'cash_loan': {
            'uz': "Naqd qarz summasini kiriting. Masalan: 100000 yoki 10 USD",
            'ru': "Введите сумму денежного долга. Например: 100000 или 10 USD",
            'en': "Enter cash loan amount. Example: 100000 or 10 USD",
        },
        'credit_purchase': {
            'uz': "Qarzga xarid summasini kiriting. Masalan: 100000 yoki 10 USD",
            'ru': "Введите сумму покупки в долг. Например: 100000 или 10 USD",
            'en': "Enter buy-on-credit amount. Example: 100000 or 10 USD",
        },
    }
    await callback.message.answer(f"{hint[debt_kind][lang]}\nDefault: {user.default_currency}")
    await callback.answer()


@router.message(DebtStates.waiting_add_amount)
async def process_add_amount(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = _normalize_lang(user.language_code)
    try:
        amount, currency = _parse_amount_and_currency(message.text, user.default_currency)
    except (InvalidOperation, TypeError):
        await message.answer(get_text('err_invalid_amount', lang))
        return
    await state.update_data(add_amount=amount, add_currency=currency)
    await state.set_state(DebtStates.waiting_add_description)
    await message.answer(get_text('msg_debt_enter_description', lang))


@router.message(DebtStates.waiting_add_description)
async def process_add_description(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get('add_amount')
    currency = data.get('add_currency', 'UZS')
    debt_kind = data.get('add_kind', 'credit_purchase')
    description = (message.text or '').strip() or None

    user = await _load_user(message)
    lang = _normalize_lang(user.language_code)
    try:
        await create_debt(user.id, amount, currency, description, debt_kind)
    except Exception as exc:
        await state.clear()
        await message.answer(str(exc))
        return

    await state.clear()
    ok = {
        'cash_loan': {
            'uz': "✅ Naqd qarz qo'shildi va balansga tushdi",
            'ru': '✅ Денежный долг добавлен и попал в баланс',
            'en': '✅ Cash loan added to main balance',
        },
        'credit_purchase': {
            'uz': "✅ Qarzga xarid qo'shildi",
            'ru': '✅ Покупка в долг добавлена',
            'en': '✅ Buy-on-credit debt added',
        },
    }
    await message.answer(ok[debt_kind][lang])

    debts = await list_debts(user.id)
    await message.answer(_render_debts(debts, lang), parse_mode='HTML', reply_markup=_debts_keyboard(lang))


@router.callback_query(F.data == 'debt_pay_list')
async def callback_pay_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await _load_user(callback)
    lang = _normalize_lang(user.language_code)
    debts = [d for d in await list_debts(user.id) if d['remaining'] > 0]
    if not debts:
        await callback.answer(
            {'uz': "Ochiq qarz yo'q", 'ru': 'Нет открытых долгов', 'en': 'No open debts'}[lang],
            show_alert=True,
        )
        return
    await callback.message.answer(
        {'uz': "Qaysi qarzni to'laysiz?", 'ru': 'Какой долг погасить?', 'en': 'Select a debt to pay'}[lang],
        reply_markup=_pay_list_keyboard(debts, lang),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r'^pay_select_'))
async def callback_pay_select(callback: CallbackQuery, state: FSMContext):
    debt_id = callback.data.replace('pay_select_', '')
    user = await _load_user(callback)
    lang = _normalize_lang(user.language_code)
    debts = await list_debts(user.id)
    target = next((debt for debt in debts if debt['id'] == debt_id), None)
    if not target:
        await callback.answer({'uz': 'Qarz topilmadi', 'ru': 'Долг не найден', 'en': 'Debt not found'}[lang], show_alert=True)
        return

    await state.set_state(DebtStates.waiting_pay_amount)
    await state.update_data(debt_id=debt_id, debt_currency=target['currency'])
    remaining_text = {
        'uz': f"Qoldiq: {target['remaining']:.2f} {target['currency']}",
        'ru': f"Остаток: {target['remaining']:.2f} {target['currency']}",
        'en': f"Remaining: {target['remaining']:.2f} {target['currency']}",
    }[lang]
    await callback.message.answer(f"{get_text('msg_debt_pay_prompt', lang).format(currency=target['currency'])}\n{remaining_text}")
    await callback.answer()


@router.message(DebtStates.waiting_pay_amount)
async def process_debt_payment(message: Message, state: FSMContext):
    data = await state.get_data()
    debt_id = data.get('debt_id')
    user = await _load_user(message)
    lang = _normalize_lang(user.language_code)

    try:
        amount, _ = _parse_amount_and_currency(message.text, data.get('debt_currency') or user.default_currency)
    except (InvalidOperation, TypeError):
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
    done = {'uz': 'Qarz to\'landi', 'ru': 'Долг погашен', 'en': 'Debt paid'}[lang]
    await message.answer(f"✅ {done}: {debt['remaining']:.2f} {debt['currency']}", parse_mode='HTML')

    debts = await list_debts(user.id)
    await message.answer(_render_debts(debts, lang), parse_mode='HTML', reply_markup=_debts_keyboard(lang))


@router.message(Command('debt_add'))
async def cmd_debt_add(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = _normalize_lang(user.language_code)
    await state.clear()
    await message.answer(
        {'uz': "Qarz turini tanlang:", 'ru': 'Выберите тип долга:', 'en': 'Choose debt type:'}[lang],
        reply_markup=_debts_keyboard(lang),
    )
