"""Transfer handler - real transfer flow."""

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    get_cancel_keyboard,
    get_confirmation_keyboard,
    get_main_menu_keyboard,
    get_skip_cancel_keyboard,
    get_transfer_details_keyboard,
    get_transfers_list_keyboard,
    get_transfer_recipients_keyboard,
    get_transfer_start_keyboard,
)
from bot.services.finance import (
    create_transfer,
    get_or_create_user,
    get_transfer_details,
    list_received_transfers,
    list_sent_transfers,
    list_transfer_recipients,
    resolve_recipient,
)
from bot.states import TransferStates
from config.constants import MAX_TRANSFER_AMOUNT
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


def _normalize_lang(value: str | None) -> str:
    lang = (value or 'uz').lower()
    if lang.startswith('ru'):
        return 'ru'
    if lang.startswith('en'):
        return 'en'
    return 'uz'


def _extract_forward_user_id(message: Message) -> int | None:
    if getattr(message, 'forward_from', None):
        return message.forward_from.id

    origin = getattr(message, 'forward_origin', None)
    sender_user = getattr(origin, 'sender_user', None) if origin else None
    if sender_user:
        return sender_user.id

    return None


def _extract_forward_user_profile(message: Message) -> dict | None:
    forward_from = getattr(message, 'forward_from', None)
    if forward_from:
        return {
            'id': forward_from.id,
            'username': forward_from.username,
            'first_name': forward_from.first_name,
            'last_name': forward_from.last_name,
        }

    origin = getattr(message, 'forward_origin', None)
    sender_user = getattr(origin, 'sender_user', None) if origin else None
    if sender_user:
        return {
            'id': sender_user.id,
            'username': sender_user.username,
            'first_name': sender_user.first_name,
            'last_name': sender_user.last_name,
        }

    return None


async def _resolve_recipient_via_chat_lookup(message: Message, raw: str):
    try:
        chat = await message.bot.get_chat(raw if raw.startswith('@') else int(raw))
    except Exception:
        return None

    if getattr(chat, 'type', None) != 'private':
        return None

    return await get_or_create_user(
        telegram_id=chat.id,
        username=getattr(chat, 'username', None),
        first_name=getattr(chat, 'first_name', None) or "User",
        last_name=getattr(chat, 'last_name', None),
        language_code=getattr(chat, 'language_code', None),
    )


@router.message(Command('transfer'))
@router.message(F.text.in_([get_text('btn_transfer', 'uz'), get_text('btn_transfer', 'ru'), get_text('btn_transfer', 'en')]))
async def start_transfer(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = _normalize_lang(user.language_code)

    await state.set_state(TransferStates.waiting_for_recipient)
    prompts = {
        'uz': "💸 O'tkazma\n\nQabul qiluvchi @username, ID kiriting yoki uning xabarini forward qiling:",
        'ru': '💸 Перевод\n\nВведите @username, ID получателя или перешлите его сообщение:',
        'en': "💸 Transfer\n\nEnter recipient @username/ID or forward recipient's message:",
    }
    await message.answer(prompts.get(lang, prompts['uz']), reply_markup=get_transfer_start_keyboard(lang))


@router.callback_query(F.data == 'transfer_recipients_refresh')
async def callback_transfer_recipients_refresh(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    lang = _normalize_lang(user.language_code)
    users = await list_transfer_recipients(user.id, limit=20)
    if not users:
        await callback.answer(
            {'uz': "Ro'yxat bo'sh", 'ru': 'Список пуст', 'en': 'List is empty'}.get(lang, 'Empty'),
            show_alert=True,
        )
        return
    await callback.message.edit_reply_markup(reply_markup=get_transfer_recipients_keyboard(users, lang))
    await callback.answer()


@router.callback_query(F.data == 'transfer_recipients_list')
async def callback_transfer_recipients_list(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    lang = _normalize_lang(user.language_code)
    users = await list_transfer_recipients(user.id, limit=20)
    if not users:
        await callback.answer(
            {'uz': "Ro'yxat bo'sh", 'ru': 'Список пуст', 'en': 'List is empty'}.get(lang, 'Empty'),
            show_alert=True,
        )
        return
    await state.set_state(TransferStates.waiting_for_recipient)
    await callback.message.answer(
        {'uz': "Qabul qiluvchini tanlang:", 'ru': 'Выберите получателя:', 'en': 'Select recipient:'}.get(lang, 'Select'),
        reply_markup=get_transfer_recipients_keyboard(users, lang),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r'^transfer_recipient_'))
async def callback_select_recipient(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    lang = _normalize_lang(user.language_code)
    target_id = int(callback.data.split('_')[-1])
    await state.update_data(recipient_id=target_id)
    await state.set_state(TransferStates.waiting_for_amount)
    prompts = {
        'uz': f"✅ Qabul qiluvchi tanlandi\nSummani kiriting ({user.default_currency}):",
        'ru': f"✅ Получатель выбран\nВведите сумму ({user.default_currency}):",
        'en': f"✅ Recipient selected\nEnter amount ({user.default_currency}):",
    }
    await callback.message.answer(prompts.get(lang, prompts['uz']), reply_markup=get_cancel_keyboard(lang))
    await callback.answer()


@router.message(TransferStates.waiting_for_recipient)
async def process_recipient(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = _normalize_lang(user.language_code)
    forwarded_profile = _extract_forward_user_profile(message)

    recipient = await resolve_recipient(
        requester_id=user.id,
        text=message.text,
        forwarded_user_id=forwarded_profile['id'] if forwarded_profile else _extract_forward_user_id(message),
        forwarded_username=forwarded_profile.get('username') if forwarded_profile else None,
        forwarded_first_name=forwarded_profile.get('first_name') if forwarded_profile else None,
        forwarded_last_name=forwarded_profile.get('last_name') if forwarded_profile else None,
    )

    raw = (message.text or '').strip()
    if not recipient and raw and (raw.startswith('@') or raw.isdigit()):
        recipient = await _resolve_recipient_via_chat_lookup(message, raw)

    if not recipient:
        errors = {
            'uz': "❌ Foydalanuvchi topilmadi. @username, ID yuboring yoki user xabarini forward qiling.",
            'ru': '❌ Пользователь не найден. Отправьте @username, ID или пересланное сообщение.',
            'en': '❌ Recipient not found. Send @username, ID, or forwarded message.',
        }
        await message.answer(errors.get(lang, errors['uz']))
        return

    recipient_name = f"@{recipient.username}" if recipient.username else str(recipient.id)
    await state.update_data(recipient_id=recipient.id, recipient_name=recipient_name)
    await state.set_state(TransferStates.waiting_for_amount)

    prompts = {
        'uz': f"✅ Qabul qiluvchi: {recipient_name}\n\nSummani kiriting ({user.default_currency}):",
        'ru': f"✅ Получатель: {recipient_name}\n\nВведите сумму ({user.default_currency}):",
        'en': f"✅ Recipient: {recipient_name}\n\nEnter amount ({user.default_currency}):",
    }
    await message.answer(prompts.get(lang, prompts['uz']), reply_markup=get_cancel_keyboard(lang))


@router.message(TransferStates.waiting_for_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = user.language_code

    try:
        amount = Decimal(message.text.replace(',', '.').replace(' ', ''))
    except (AttributeError, InvalidOperation):
        errors = {
            'uz': "❌ Noto'g'ri summa. Masalan: 1200.50",
            'ru': '❌ Некорректная сумма. Пример: 1200.50',
            'en': '❌ Invalid amount. Example: 1200.50',
        }
        await message.answer(errors.get(lang, errors['uz']))
        return

    if amount <= 0:
        await message.answer("❌ Summa musbat bo'lishi kerak.")
        return

    if amount > Decimal(str(MAX_TRANSFER_AMOUNT)):
        await message.answer(f"❌ Limitdan oshib ketdi: {MAX_TRANSFER_AMOUNT}")
        return

    await state.update_data(amount=str(amount), currency=user.default_currency)
    await state.set_state(TransferStates.waiting_for_description)

    prompts = {
        'uz': f"✅ Summa: {amount} {user.default_currency}\n\nIzoh kiriting yoki O'tkazib yuborish tugmasini bosing:",
        'ru': f"✅ Сумма: {amount} {user.default_currency}\n\nВведите комментарий или нажмите Пропустить:",
        'en': f"✅ Amount: {amount} {user.default_currency}\n\nEnter comment or press Skip:",
    }
    await message.answer(prompts.get(lang, prompts['uz']), reply_markup=get_skip_cancel_keyboard(lang))


@router.message(TransferStates.waiting_for_description)
async def process_transfer_description(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = user.language_code

    if message.text == get_text('btn_skip', lang):
        description = None
    else:
        description = message.text

    await state.update_data(description=description)
    data = await state.get_data()

    confirmation = {
        'uz': (
            '📋 <b>O\'tkazmani tasdiqlang</b>\n\n'
            f"👤 Qabul qiluvchi: {data['recipient_name']}\n"
            f"💰 Summa: {data['amount']} {data['currency']}\n"
            f"💬 Izoh: {description or '-'}"
        ),
        'ru': (
            '📋 <b>Подтверждение перевода</b>\n\n'
            f"👤 Получатель: {data['recipient_name']}\n"
            f"💰 Сумма: {data['amount']} {data['currency']}\n"
            f"💬 Комментарий: {description or '-'}"
        ),
        'en': (
            '<b>📋 Transfer confirmation</b>\n\n'
            f"👤 Recipient: {data['recipient_name']}\n"
            f"💰 Amount: {data['amount']} {data['currency']}\n"
            f"💬 Comment: {description or '-'}"
        ),
    }

    await state.set_state(TransferStates.waiting_for_confirmation)
    await message.answer(
        confirmation.get(lang, confirmation['uz']),
        parse_mode='HTML',
        reply_markup=get_confirmation_keyboard('confirm_transfer', lang=lang),
    )


@router.callback_query(TransferStates.waiting_for_confirmation, F.data == 'confirm_transfer')
async def confirm_transfer_callback(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    lang = user.language_code
    data = await state.get_data()

    try:
        await create_transfer(
            sender_id=user.id,
            recipient_id=int(data['recipient_id']),
            amount=Decimal(str(data['amount'])),
            description=data.get('description'),
            currency=data.get('currency') or user.default_currency,
        )
    except Exception as exc:
        errors = {
            'uz': f"❌ O'tkazma bajarilmadi: {exc}",
            'ru': f"❌ Перевод не выполнен: {exc}",
            'en': f"❌ Transfer failed: {exc}",
        }
        await callback.message.edit_text(errors.get(lang, errors['uz']))
        await state.clear()
        await callback.answer()
        return

    success = {
        'uz': f"✅ {data['amount']} {data['currency']} {data['recipient_name']} ga yuborildi.",
        'ru': f"✅ {data['amount']} {data['currency']} отправлены {data['recipient_name']}.",
        'en': f"✅ {data['amount']} {data['currency']} sent to {data['recipient_name']}",
    }

    await callback.message.edit_text(success.get(lang, success['uz']))
    await callback.message.answer(
        get_text('msg_main_menu', lang),
        reply_markup=get_main_menu_keyboard(lang, settings.MINIAPP_URL or None),
    )
    await state.clear()
    await callback.answer()


@router.message(Command('transfers'))
async def show_transfers(message: Message):
    user = await _load_user(message)
    lang = user.language_code

    transfers = await list_sent_transfers(user.id)
    if not transfers:
        empty = {'uz': "📭 Hali o'tkazmalar yo'q", 'ru': '📭 Пока нет переводов', 'en': '📭 No transfers yet'}
        await message.answer(empty.get(lang, empty['uz']))
        return

    title = {'uz': "📤 <b>Yuborilgan o'tkazmalar</b>", 'ru': '📤 <b>Отправленные переводы</b>', 'en': '📤 <b>Sent transfers</b>'}
    await message.answer(
        title.get(lang, title['uz']),
        parse_mode='HTML',
        reply_markup=get_transfers_list_keyboard(transfers, lang=lang),
    )


@router.callback_query(F.data.regexp(r'^transfer_[0-9a-fA-F-]+$'))
async def show_transfer_details_callback(callback: CallbackQuery):
    user = await _load_user(callback)
    lang = user.language_code

    transfer_id = callback.data.split('_', 1)[1]
    details = await get_transfer_details(transfer_id, user.id)
    if not details:
        await callback.answer('Not found', show_alert=True)
        return

    expenses_text = '\n'.join(
        [
            f"• {item['amount']} {item['currency']} - {item['category']} - {item['description']} ({item['date']})"
            for item in details['expenses']
        ]
    )
    if not expenses_text:
        expenses_text = '-' 

    text = (
        f"📊 <b>{details['recipient']}</b>\n\n"
        f"💰 {details['amount']} {details['currency']}\n"
        f"💬 {details['description']}\n"
        f"💸 Ishlatilgan: {details['spent']} {details['currency']}\n"
        f"💵 Qolgan: {details['remaining']} {details['currency']}\n"
        f"📅 {details['created_at']}\n\n"
        f"🧾 Xarajatlar:\n{expenses_text}"
    )

    await callback.message.edit_text(
        text,
        parse_mode='HTML',
        reply_markup=get_transfer_details_keyboard(transfer_id, lang=lang),
    )
    await callback.answer()


@router.message(Command('received'))
async def show_received_transfers_handler(message: Message):
    user = await _load_user(message)
    lang = user.language_code

    transfers = await list_received_transfers(user.id)
    if not transfers:
        empty = {'uz': "📭 Qabul qilingan o'tkazmalar yo'q", 'ru': '📭 Нет полученных переводов', 'en': '📭 No received transfers'}
        await message.answer(empty.get(lang, empty['uz']))
        return

    title = {'uz': "📥 <b>Qabul qilingan o'tkazmalar</b>", 'ru': '📥 <b>Полученные переводы</b>', 'en': '📥 <b>Received transfers</b>'}
    await message.answer(
        title.get(lang, title['uz']),
        parse_mode='HTML',
        reply_markup=get_transfers_list_keyboard(transfers, lang=lang),
    )
