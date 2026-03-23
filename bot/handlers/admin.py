from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    get_admin_user_actions_keyboard,
    get_admin_user_delete_confirm_keyboard,
    get_admin_users_keyboard,
)
from bot.services.finance import (
    delete_user_for_admin,
    get_or_create_user,
    get_user_admin_snapshot,
    is_admin,
    list_users_for_admin,
    set_user_admin_role,
    set_user_total_balance_for_admin,
)

router = Router()


class AdminStates(StatesGroup):
    waiting_for_balance_value = State()


async def _load_user(message_or_callback):
    src = message_or_callback.from_user
    return await get_or_create_user(
        telegram_id=src.id,
        username=src.username,
        first_name=src.first_name,
        last_name=src.last_name,
        language_code=src.language_code,
    )


def _tr(lang: str, uz: str, ru: str, en: str) -> str:
    if lang == 'ru':
        return ru
    if lang == 'en':
        return en
    return uz


def _render_users_text(users: list[dict], lang: str) -> str:
    if not users:
        return _tr(lang, 'Foydalanuvchilar topilmadi.', 'Пользователи не найдены.', 'No users found.')

    title = _tr(lang, '👥 <b>Foydalanuvchilar</b>', '👥 <b>Пользователи</b>', '👥 <b>Users</b>')
    lines = [title, '']
    for user in users:
        role = 'ADMIN' if user.get('is_admin') else 'USER'
        active = '✅' if user.get('is_active') else '⛔'
        username = f"@{user['username']}" if user.get('username') else str(user['id'])
        full_name = f"{user.get('first_name') or ''} {user.get('last_name') or ''}".strip() or username
        lines.append(f"{active} <b>{full_name}</b> ({username})")
        lines.append(f"ID: <code>{user['id']}</code> · {role} · {user.get('default_currency', '-')}")
        lines.append('')
    return '\n'.join(lines)


def _render_user_detail(snapshot: dict, lang: str) -> str:
    username = f"@{snapshot['username']}" if snapshot.get('username') else str(snapshot['id'])
    full_name = f"{snapshot.get('first_name') or ''} {snapshot.get('last_name') or ''}".strip() or username
    role_text = _tr(lang, 'ADMIN', 'АДМИН', 'ADMIN') if snapshot.get('is_admin') else 'USER'
    status_text = _tr(lang, 'Faol', 'Активен', 'Active') if snapshot.get('is_active') else _tr(lang, 'Nofaol', 'Неактивен', 'Inactive')
    own_label = _tr(lang, "O'z mablag'i", 'Собственные', 'Own')

    return (
        f"👤 <b>{full_name}</b>\n"
        f"🔗 {username}\n"
        f"🆔 <code>{snapshot['id']}</code>\n"
        f"🛡 {role_text} · {status_text}\n"
        f"🌐 {snapshot.get('language_code') or '-'} · 💱 {snapshot.get('default_currency') or '-'}\n\n"
        f"💰 <b>{_tr(lang, 'Balans', 'Баланс', 'Balance')}</b>\n"
        f"• {_tr(lang, 'Umumiy', 'Общий', 'Total')}: <b>{snapshot['total_balance']:.2f} {snapshot['currency']}</b>\n"
        f"• {own_label}: {snapshot['own_balance']:.2f} {snapshot['currency']}\n"
        f"• {_tr(lang, 'Qabul qilingan', 'Полученные', 'Received')}: {snapshot['received_balance']:.2f} {snapshot['currency']}"
    )


def _localize_service_error(lang: str, raw: str) -> str:
    mapping = {
        'Admin access required': _tr(lang, "Ruxsat yo'q", 'Доступ запрещён', 'Access denied'),
        'User not found': _tr(lang, 'Foydalanuvchi topilmadi', 'Пользователь не найден', 'User not found'),
        'Cannot remove your own admin role': _tr(
            lang,
            "O'zingizning admin rolingizni olib tashlay olmaysiz",
            'Нельзя снять свою роль администратора',
            'Cannot remove your own admin role',
        ),
        'Cannot delete yourself': _tr(lang, "O'zingizni o'chira olmaysiz", 'Нельзя удалить самого себя', 'Cannot delete yourself'),
    }
    return mapping.get(raw, raw)


def _parse_balance_input(raw: str, fallback_currency: str) -> tuple[Decimal, str]:
    text = (raw or '').strip().replace(',', '.')
    if not text:
        raise ValueError('empty')

    parts = text.split()
    try:
        amount = Decimal(parts[0])
    except (InvalidOperation, IndexError):
        raise ValueError('invalid_amount')

    if amount < 0:
        raise ValueError('negative_amount')

    currency = (parts[1].upper() if len(parts) > 1 else fallback_currency.upper())
    if currency not in {'UZS', 'USD'}:
        raise ValueError('invalid_currency')

    return amount.quantize(Decimal('0.01')), currency


@router.message(Command('users'))
async def cmd_users(message: Message):
    user = await _load_user(message)
    lang = user.language_code
    if not await is_admin(user.id):
        await message.answer(_tr(lang, "❌ Ruxsat yo'q", '❌ Доступ запрещён', '❌ Access denied'))
        return

    query = (message.text or '').split(maxsplit=1)
    search = query[1] if len(query) > 1 else None
    users = await list_users_for_admin(user.id, search=search, limit=20)
    await message.answer(
        _render_users_text(users, lang),
        parse_mode='HTML',
        reply_markup=get_admin_users_keyboard(users, lang=lang),
    )


@router.callback_query(F.data == 'admin_users')
async def callback_admin_users(callback: CallbackQuery):
    user = await _load_user(callback)
    lang = user.language_code
    if not await is_admin(user.id):
        await callback.answer(_tr(lang, "Ruxsat yo'q", 'Доступ запрещён', 'Access denied'), show_alert=True)
        return

    users = await list_users_for_admin(user.id, limit=20)
    await callback.message.edit_text(
        _render_users_text(users, lang),
        parse_mode='HTML',
        reply_markup=get_admin_users_keyboard(users, lang=lang),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r'^admin_user_role_\d+_[01]$'))
async def callback_toggle_admin_role(callback: CallbackQuery):
    user = await _load_user(callback)
    lang = user.language_code

    if not await is_admin(user.id):
        await callback.answer(_tr(lang, "Ruxsat yo'q", 'Доступ запрещён', 'Access denied'), show_alert=True)
        return

    _, _, _, target_id_raw, current_state_raw = callback.data.split('_')
    target_id = int(target_id_raw)
    current_state = int(current_state_raw)
    new_state = not bool(current_state)

    try:
        await set_user_admin_role(user.id, target_id, new_state)
        snapshot = await get_user_admin_snapshot(user.id, target_id)
    except Exception as exc:
        await callback.answer(_localize_service_error(lang, str(exc)), show_alert=True)
        return

    await callback.message.edit_text(
        _render_user_detail(snapshot, lang),
        parse_mode='HTML',
        reply_markup=get_admin_user_actions_keyboard(target_id, snapshot['is_admin'], lang=lang),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r'^admin_user_reset_\d+$'))
async def callback_reset_user_balance(callback: CallbackQuery):
    user = await _load_user(callback)
    lang = user.language_code

    if not await is_admin(user.id):
        await callback.answer(_tr(lang, "Ruxsat yo'q", 'Доступ запрещён', 'Access denied'), show_alert=True)
        return

    target_id = int(callback.data.rsplit('_', 1)[1])

    try:
        snapshot = await get_user_admin_snapshot(user.id, target_id)
        await set_user_total_balance_for_admin(
            admin_user_id=user.id,
            target_user_id=target_id,
            target_total=Decimal('0'),
            currency=snapshot['currency'],
        )
        updated = await get_user_admin_snapshot(user.id, target_id)
    except Exception as exc:
        await callback.answer(_localize_service_error(lang, str(exc)), show_alert=True)
        return

    await callback.message.edit_text(
        _render_user_detail(updated, lang),
        parse_mode='HTML',
        reply_markup=get_admin_user_actions_keyboard(target_id, updated['is_admin'], lang=lang),
    )
    await callback.answer(_tr(lang, 'Balans 0 qilindi', 'Баланс обнулён', 'Balance reset'))


@router.callback_query(F.data.regexp(r'^admin_user_set_\d+$'))
async def callback_set_user_balance(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    lang = user.language_code

    if not await is_admin(user.id):
        await callback.answer(_tr(lang, "Ruxsat yo'q", 'Доступ запрещён', 'Access denied'), show_alert=True)
        return

    target_id = int(callback.data.rsplit('_', 1)[1])
    try:
        snapshot = await get_user_admin_snapshot(user.id, target_id)
    except Exception as exc:
        await callback.answer(_localize_service_error(lang, str(exc)), show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_balance_value)
    await state.update_data(target_user_id=target_id)

    prompt = _tr(
        lang,
        f"Yangi umumiy balansni kiriting.\nMasalan: <code>100000 UZS</code> yoki <code>150 USD</code>\n\nJoriy: {snapshot['total_balance']:.2f} {snapshot['currency']}",
        f"Введите новый общий баланс.\nНапример: <code>100000 UZS</code> или <code>150 USD</code>\n\nТекущий: {snapshot['total_balance']:.2f} {snapshot['currency']}",
        f"Enter new total balance.\nExample: <code>100000 UZS</code> or <code>150 USD</code>\n\nCurrent: {snapshot['total_balance']:.2f} {snapshot['currency']}",
    )

    await callback.message.edit_text(prompt, parse_mode='HTML')
    await callback.answer()


@router.message(AdminStates.waiting_for_balance_value)
async def process_set_user_balance(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = user.language_code

    if not await is_admin(user.id):
        await state.clear()
        await message.answer(_tr(lang, "❌ Ruxsat yo'q", '❌ Доступ запрещён', '❌ Access denied'))
        return

    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    if not target_user_id:
        await state.clear()
        await message.answer(_tr(lang, "❌ Foydalanuvchi topilmadi", '❌ Пользователь не найден', '❌ User not found'))
        return

    try:
        snapshot = await get_user_admin_snapshot(user.id, int(target_user_id))
        amount, currency = _parse_balance_input(message.text or '', snapshot['currency'])
    except ValueError as exc:
        code = str(exc)
        if code == 'invalid_amount':
            await message.answer(_tr(lang, "❌ Noto'g'ri summa", '❌ Некорректная сумма', '❌ Invalid amount'))
        elif code == 'negative_amount':
            await message.answer(_tr(lang, "❌ Summa manfiy bo'lishi mumkin emas", '❌ Сумма не может быть отрицательной', '❌ Amount cannot be negative'))
        elif code == 'invalid_currency':
            await message.answer(_tr(lang, "❌ Faqat UZS yoki USD kiriting", '❌ Используйте только UZS или USD', '❌ Use only UZS or USD'))
        else:
            await message.answer(_tr(lang, "❌ Noto'g'ri format", '❌ Неверный формат', '❌ Invalid format'))
        return
    except Exception as exc:
        await state.clear()
        await message.answer(f"❌ {_localize_service_error(lang, str(exc))}")
        return

    try:
        await set_user_total_balance_for_admin(
            admin_user_id=user.id,
            target_user_id=int(target_user_id),
            target_total=amount,
            currency=currency,
        )
        updated = await get_user_admin_snapshot(user.id, int(target_user_id), currency=currency)
    except Exception as exc:
        await state.clear()
        await message.answer(f"❌ {_localize_service_error(lang, str(exc))}")
        return

    await state.clear()
    await message.answer(
        _render_user_detail(updated, lang),
        parse_mode='HTML',
        reply_markup=get_admin_user_actions_keyboard(updated['id'], updated['is_admin'], lang=lang),
    )


@router.callback_query(F.data.regexp(r'^admin_user_delete_confirm_\d+$'))
async def callback_confirm_delete_user(callback: CallbackQuery):
    user = await _load_user(callback)
    lang = user.language_code

    if not await is_admin(user.id):
        await callback.answer(_tr(lang, "Ruxsat yo'q", 'Доступ запрещён', 'Access denied'), show_alert=True)
        return

    target_id = int(callback.data.rsplit('_', 1)[1])

    try:
        await delete_user_for_admin(user.id, target_id)
    except Exception as exc:
        await callback.answer(_localize_service_error(lang, str(exc)), show_alert=True)
        return

    users = await list_users_for_admin(user.id, limit=20)
    await callback.message.edit_text(
        _render_users_text(users, lang),
        parse_mode='HTML',
        reply_markup=get_admin_users_keyboard(users, lang=lang),
    )
    await callback.answer(_tr(lang, "User o'chirildi", 'Пользователь удалён', 'User deleted'))


@router.callback_query(F.data.regexp(r'^admin_user_delete_\d+$'))
async def callback_delete_user(callback: CallbackQuery):
    user = await _load_user(callback)
    lang = user.language_code

    if not await is_admin(user.id):
        await callback.answer(_tr(lang, "Ruxsat yo'q", 'Доступ запрещён', 'Access denied'), show_alert=True)
        return

    target_id = int(callback.data.rsplit('_', 1)[1])
    try:
        snapshot = await get_user_admin_snapshot(user.id, target_id)
    except Exception as exc:
        await callback.answer(_localize_service_error(lang, str(exc)), show_alert=True)
        return

    confirm_text = _tr(
        lang,
        f"⚠️ <b>{snapshot['first_name']}</b> (ID: <code>{target_id}</code>) userni o'chirishni tasdiqlaysizmi?",
        f"⚠️ Подтвердите удаление пользователя <b>{snapshot['first_name']}</b> (ID: <code>{target_id}</code>)",
        f"⚠️ Confirm deletion of user <b>{snapshot['first_name']}</b> (ID: <code>{target_id}</code>)",
    )

    await callback.message.edit_text(
        confirm_text,
        parse_mode='HTML',
        reply_markup=get_admin_user_delete_confirm_keyboard(target_id, lang=lang),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r'^admin_user_\d+$'))
async def callback_admin_user_details(callback: CallbackQuery):
    user = await _load_user(callback)
    lang = user.language_code
    if not await is_admin(user.id):
        await callback.answer(_tr(lang, "Ruxsat yo'q", 'Доступ запрещён', 'Access denied'), show_alert=True)
        return

    target_id = int(callback.data.rsplit('_', 1)[1])

    try:
        snapshot = await get_user_admin_snapshot(user.id, target_id)
    except Exception as exc:
        await callback.answer(_localize_service_error(lang, str(exc)), show_alert=True)
        return

    await callback.message.edit_text(
        _render_user_detail(snapshot, lang),
        parse_mode='HTML',
        reply_markup=get_admin_user_actions_keyboard(target_id, snapshot['is_admin'], lang=lang),
    )
    await callback.answer()
