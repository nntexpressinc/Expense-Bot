"""Start command handler."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import MenuButtonWebApp, Message, WebAppInfo

from bot.keyboards import get_main_menu_keyboard, get_miniapp_launch_keyboard
from bot.services.finance import get_or_create_user, join_user_group
from config.i18n import get_text
from config.settings import settings

router = Router()
logger = logging.getLogger(__name__)


def _normalize_lang(value: str | None) -> str:
    lang = (value or 'uz').lower()
    if lang.startswith('ru'):
        return 'ru'
    if lang.startswith('en'):
        return 'en'
    return 'uz'


async def _prepare_user(message: Message):
    return await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
    )


def _get_safe_miniapp_url() -> str | None:
    if not settings.MINIAPP_URL:
        return None
    return settings.MINIAPP_URL.rstrip('/') + '/'


async def _set_chat_menu_button(message: Message, lang: str) -> None:
    safe_miniapp_url = _get_safe_miniapp_url()
    if not safe_miniapp_url:
        return

    try:
        await message.bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(
                text=get_text('btn_open_miniapp', lang),
                web_app=WebAppInfo(url=safe_miniapp_url),
            ),
        )
    except Exception as exc:
        logger.warning("Failed to set chat menu button for %s: %s", message.chat.id, exc)


async def _send_miniapp_launcher(message: Message, lang: str) -> None:
    await _set_chat_menu_button(message, lang)
    reply_markup = get_miniapp_launch_keyboard(lang=lang, miniapp_url=_get_safe_miniapp_url())
    if not reply_markup:
        await message.answer(get_text('msg_open_miniapp_unavailable', lang))
        return

    await message.answer(
        get_text('msg_open_miniapp_prompt', lang),
        reply_markup=reply_markup,
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await _prepare_user(message)
    lang = user.language_code or 'uz'
    parts = (message.text or '').split(maxsplit=1)
    deep_link = parts[1].strip() if len(parts) > 1 else ''

    if deep_link.startswith('join_'):
        try:
            inviter_id = int(deep_link.replace('join_', '', 1))
            if inviter_id != user.id:
                await join_user_group(inviter_id, user.id)
                join_text = {
                    'uz': "Siz guruhga qo'shildingiz.",
                    'ru': 'Вы добавлены в группу.',
                    'en': 'You were added to the group.',
                }
                await message.answer(join_text.get(lang, join_text['en']))
        except Exception:
            error_text = {
                'uz': "Guruhga qo'shish linki ishlamadi.",
                'ru': 'Ссылка приглашения не сработала.',
                'en': 'Invite link could not be applied.',
            }
            await message.answer(error_text.get(lang, error_text['en']))

    await message.answer(
        get_text('msg_welcome', lang),
        reply_markup=get_main_menu_keyboard(lang=lang, miniapp_url=settings.MINIAPP_URL or None),
    )
    await _send_miniapp_launcher(message, lang)


@router.message(Command('help'))
@router.message(F.text.in_([get_text('btn_help', 'uz'), get_text('btn_help', 'ru'), get_text('btn_help', 'en')]))
async def cmd_help(message: Message):
    user = await _prepare_user(message)
    await message.answer(get_text('msg_help', user.language_code))


@router.message(Command('cancel'))
@router.message(F.text.in_([get_text('btn_cancel', 'uz'), get_text('btn_cancel', 'ru'), get_text('btn_cancel', 'en')]))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    user = await _prepare_user(message)
    lang = user.language_code
    await message.answer(
        get_text('msg_operation_cancelled', lang),
        reply_markup=get_main_menu_keyboard(lang=lang, miniapp_url=settings.MINIAPP_URL or None),
    )


@router.message(Command('menu'))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    user = await _prepare_user(message)
    lang = user.language_code
    await message.answer(
        get_text('msg_main_menu', lang),
        reply_markup=get_main_menu_keyboard(lang=lang, miniapp_url=settings.MINIAPP_URL or None),
    )
    await _send_miniapp_launcher(message, lang)


@router.message(Command('app'))
@router.message(F.text.in_([get_text('btn_open_miniapp', 'uz'), get_text('btn_open_miniapp', 'ru'), get_text('btn_open_miniapp', 'en')]))
async def open_miniapp(message: Message):
    user = await _prepare_user(message)
    await _send_miniapp_launcher(message, user.language_code or 'uz')


@router.message(Command('invite'))
@router.message(F.text.in_([get_text('btn_invite', 'uz'), get_text('btn_invite', 'ru'), get_text('btn_invite', 'en')]))
async def cmd_invite(message: Message):
    user = await _prepare_user(message)
    lang = _normalize_lang(user.language_code)

    me = await message.bot.get_me()
    link = f"https://t.me/{me.username}?start=join_{user.id}"
    text = {
        'uz': f"Guruhga qo'shish linki:\n{link}",
        'ru': f"Ссылка для добавления в группу:\n{link}",
        'en': f"Group invite link:\n{link}",
    }
    await message.answer(text.get(lang, text['en']))
