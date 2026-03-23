"""Settings handler."""

from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    get_admin_keyboard,
    get_currency_keyboard,
    get_groups_keyboard,
    get_language_keyboard,
    get_main_menu_keyboard,
    get_settings_keyboard,
)
from bot.services.finance import (
    get_or_create_user,
    get_user_groups,
    is_admin,
    read_exchange_rate,
    set_user_active_group,
    set_user_currency,
    set_user_language,
    update_exchange_rate,
)
from config.i18n import get_text
from config.settings import settings

router = Router()


class SettingsStates(StatesGroup):
    waiting_for_exchange_rate = State()


async def _load_user(callback_or_message):
    src = callback_or_message.from_user
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


async def _settings_payload(source_user) -> tuple:
    user = await get_or_create_user(
        telegram_id=source_user.id,
        username=source_user.username,
        first_name=source_user.first_name,
        last_name=source_user.last_name,
        language_code=source_user.language_code,
    )
    groups = await get_user_groups(user.id)
    active_group = next((group for group in groups if group.get('id') == user.active_group_id), None)
    return user, groups, active_group


def _settings_text(lang: str, active_group_name: str | None) -> str:
    base = get_text('msg_settings', lang)
    if not active_group_name:
        return base
    return f"{base}\n\n{get_text('msg_active_group', lang)}: <b>{active_group_name}</b>"


@router.message(Command('settings'))
@router.message(F.text.in_([get_text('btn_settings', 'uz'), get_text('btn_settings', 'ru'), get_text('btn_settings', 'en')]))
async def cmd_settings(message: Message, state: FSMContext):
    await state.clear()
    user = await _load_user(message)
    user_is_admin = await is_admin(user.id)
    groups = await get_user_groups(user.id)
    active_group = next((group for group in groups if group.get('id') == user.active_group_id), None)

    await message.answer(
        _settings_text(user.language_code, active_group.get('name') if active_group else None),
        reply_markup=get_settings_keyboard(user.language_code, user_is_admin, can_switch_group=len(groups) > 1),
    )


@router.message(Command('language'))
async def cmd_language(message: Message):
    user = await _load_user(message)
    await message.answer(
        get_text('msg_select_language', user.language_code),
        reply_markup=get_language_keyboard(),
    )


@router.message(Command('currency'))
async def cmd_currency(message: Message):
    user = await _load_user(message)
    await message.answer(
        get_text('msg_select_currency', user.language_code),
        reply_markup=get_currency_keyboard(),
    )


@router.callback_query(F.data == 'settings_menu')
async def callback_settings_menu(callback: CallbackQuery):
    user = await _load_user(callback)
    user_is_admin = await is_admin(user.id)
    groups = await get_user_groups(user.id)
    active_group = next((group for group in groups if group.get('id') == user.active_group_id), None)

    await callback.message.edit_text(
        _settings_text(user.language_code, active_group.get('name') if active_group else None),
        reply_markup=get_settings_keyboard(user.language_code, user_is_admin, can_switch_group=len(groups) > 1),
    )
    await callback.answer()


@router.callback_query(F.data == 'settings_language')
async def callback_language_selection(callback: CallbackQuery):
    user = await _load_user(callback)

    await callback.message.edit_text(
        get_text('msg_select_language', user.language_code),
        reply_markup=get_language_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith('lang_'))
async def callback_set_language(callback: CallbackQuery):
    new_lang = callback.data.split('_')[1]
    await set_user_language(callback.from_user.id, new_lang)

    await callback.message.edit_text(get_text('msg_language_changed', new_lang))
    await callback.message.answer(
        get_text('msg_main_menu', new_lang),
        reply_markup=get_main_menu_keyboard(new_lang, settings.MINIAPP_URL or None),
    )
    await callback.answer()


@router.callback_query(F.data == 'settings_currency')
async def callback_currency_selection(callback: CallbackQuery):
    user = await _load_user(callback)

    await callback.message.edit_text(
        get_text('msg_select_currency', user.language_code),
        reply_markup=get_currency_keyboard(),
    )
    await callback.answer()


@router.message(Command('group'))
async def cmd_group(message: Message):
    user, groups, active_group = await _settings_payload(message.from_user)
    lang = user.language_code

    if not groups:
        await message.answer(get_text('msg_no_groups', lang))
        return

    if len(groups) == 1:
        await message.answer(
            f"{get_text('msg_only_one_group', lang)}\n\n{get_text('msg_active_group', lang)}: <b>{groups[0]['name']}</b>"
        )
        return

    await message.answer(
        f"{get_text('msg_select_group', lang)}\n\n{get_text('msg_active_group', lang)}: <b>{active_group.get('name') if active_group else '-'}</b>",
        reply_markup=get_groups_keyboard(groups, user.active_group_id, lang),
    )


@router.callback_query(F.data == 'settings_group')
async def callback_group_selection(callback: CallbackQuery):
    user, groups, active_group = await _settings_payload(callback.from_user)
    lang = user.language_code

    if not groups:
        await callback.answer(get_text('msg_no_groups', lang), show_alert=True)
        return

    if len(groups) == 1:
        await callback.answer(get_text('msg_only_one_group', lang), show_alert=True)
        return

    await callback.message.edit_text(
        f"{get_text('msg_select_group', lang)}\n\n{get_text('msg_active_group', lang)}: <b>{active_group.get('name') if active_group else '-'}</b>",
        reply_markup=get_groups_keyboard(groups, user.active_group_id, lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith('settings_group_'))
async def callback_set_group(callback: CallbackQuery):
    user = await _load_user(callback)
    lang = user.language_code

    try:
        group_id = int(callback.data.rsplit('_', 1)[1])
    except (TypeError, ValueError):
        await callback.answer(_tr(lang, "Noto'g'ri guruh", 'Неверная группа', 'Invalid group'), show_alert=True)
        return

    try:
        group = await set_user_active_group(user.id, group_id)
    except ValueError:
        await callback.answer(_tr(lang, "Guruhga ruxsat yo'q", 'Нет доступа к группе', 'No access to this group'), show_alert=True)
        return

    updated_user, groups, _ = await _settings_payload(callback.from_user)
    user_is_admin = await is_admin(updated_user.id)

    await callback.message.edit_text(
        f"{get_text('msg_group_changed', lang)}\n\n{get_text('msg_active_group', lang)}: <b>{group.name}</b>",
        reply_markup=get_settings_keyboard(updated_user.language_code, user_is_admin, can_switch_group=len(groups) > 1),
    )
    await callback.answer()


@router.callback_query(F.data.startswith('currency_'))
async def callback_set_currency(callback: CallbackQuery):
    new_currency = callback.data.split('_')[1]
    user = await _load_user(callback)
    lang = user.language_code
    await set_user_currency(user.id, new_currency)

    await callback.message.edit_text(
        f"{get_text('msg_currency_changed', lang)}\n\n💱 {new_currency}"
    )
    await callback.answer()


@router.callback_query(F.data == 'admin_panel')
async def callback_admin_panel(callback: CallbackQuery):
    user = await _load_user(callback)
    if not await is_admin(user.id):
        await callback.answer(
            _tr(user.language_code, "Ruxsat yo'q", 'Доступ запрещён', 'Access denied'),
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        get_text('msg_admin_panel', user.language_code),
        reply_markup=get_admin_keyboard(user.language_code),
    )
    await callback.answer()


@router.callback_query(F.data == 'admin_exchange_rate')
async def callback_exchange_rate_menu(callback: CallbackQuery, state: FSMContext):
    user = await _load_user(callback)
    if not await is_admin(user.id):
        await callback.answer(
            _tr(user.language_code, "Ruxsat yo'q", 'Доступ запрещён', 'Access denied'),
            show_alert=True,
        )
        return

    current_rate = await read_exchange_rate('USD', 'UZS')
    lang = user.language_code

    prompt = {
        'uz': f"💱 Joriy kurs: 1 USD = {current_rate} UZS\n\nYangi kursni kiriting:",
        'ru': f"💱 Текущий курс: 1 USD = {current_rate} UZS\n\nВведите новый курс:",
        'en': f"💱 Current rate: 1 USD = {current_rate} UZS\n\nEnter new rate:",
    }

    await callback.message.edit_text(prompt.get(lang, prompt['uz']))
    await state.set_state(SettingsStates.waiting_for_exchange_rate)
    await callback.answer()


@router.message(SettingsStates.waiting_for_exchange_rate)
async def process_exchange_rate(message: Message, state: FSMContext):
    user = await _load_user(message)
    lang = user.language_code

    try:
        new_rate = Decimal(message.text.replace(',', '.').strip())
        if new_rate <= 0:
            raise ValueError('Rate must be positive')

        await update_exchange_rate(user.id, 'USD', 'UZS', new_rate)

        success_msg = {
            'uz': f"✅ Kurs yangilandi: 1 USD = {new_rate} UZS",
            'ru': f"✅ Курс обновлён: 1 USD = {new_rate} UZS",
            'en': f"✅ Rate updated: 1 USD = {new_rate} UZS",
        }
        await message.answer(success_msg.get(lang, success_msg['uz']))
        await state.clear()

    except Exception:
        error_msg = {
            'uz': '❌ Xato! Musbat son kiriting.',
            'ru': '❌ Ошибка! Введите положительное число.',
            'en': '❌ Error! Enter a positive number.',
        }
        await message.answer(error_msg.get(lang, error_msg['uz']))
