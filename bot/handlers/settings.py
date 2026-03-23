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
    get_language_keyboard,
    get_main_menu_keyboard,
    get_settings_keyboard,
)
from bot.services.finance import (
    get_or_create_user,
    is_admin,
    read_exchange_rate,
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


@router.message(Command('settings'))
@router.message(F.text.in_([get_text('btn_settings', 'uz'), get_text('btn_settings', 'ru'), get_text('btn_settings', 'en')]))
async def cmd_settings(message: Message, state: FSMContext):
    await state.clear()
    user = await _load_user(message)
    user_is_admin = await is_admin(user.id)

    await message.answer(
        get_text('msg_settings', user.language_code),
        reply_markup=get_settings_keyboard(user.language_code, user_is_admin),
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

    await callback.message.edit_text(
        get_text('msg_settings', user.language_code),
        reply_markup=get_settings_keyboard(user.language_code, user_is_admin),
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
