from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import select

from bot.keyboards import get_report_period_keyboard
from bot.services.finance import get_or_create_user
from config.i18n import get_text
from database.reporting import generate_report_download
from database.session import async_session_factory
from database.models import User

router = Router()


async def _load_user(message: Message):
    src = message.from_user
    return await get_or_create_user(
        telegram_id=src.id,
        username=src.username,
        first_name=src.first_name,
        last_name=src.last_name,
        language_code=src.language_code,
    )


def _normalize_lang(value: str | None) -> str:
    lang = (value or 'uz').split('-')[0].lower()
    return lang if lang in {'uz', 'ru', 'en'} else 'uz'


def _resolve_period_from_token(token: str | None) -> str | None:
    mapping = {
        'day': 'day',
        'daily': 'day',
        'week': 'week',
        'weekly': 'week',
        'month': 'month',
        'monthly': 'month',
        'year': 'year',
        'yearly': 'year',
    }
    if not token:
        return None
    return mapping.get(token.lower())


async def _generate_report_excel(user_id: int, period: str) -> tuple[bytes, str]:
    async with async_session_factory() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            raise ValueError('User not found')
        content, filename, _ = await generate_report_download(db, user, period)
        return content, filename


async def _send_period_report(chat_message: Message, user_id: int, lang: str, period: str) -> None:
    progress = {
        'uz': 'Hisobot tayyorlanmoqda...',
        'ru': '\u041f\u043e\u0434\u0433\u043e\u0442\u0430\u0432\u043b\u0438\u0432\u0430\u044e \u043e\u0442\u0447\u0451\u0442...',
        'en': 'Preparing report...',
    }
    await chat_message.answer(progress.get(lang, progress['en']))

    try:
        file_bytes, filename = await _generate_report_excel(user_id, period)
    except Exception:
        error_text = {
            'uz': "Hisobotni yaratib bo'lmadi",
            'ru': '\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u0444\u043e\u0440\u043c\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043e\u0442\u0447\u0451\u0442',
            'en': 'Failed to generate report',
        }
        await chat_message.answer(error_text.get(lang, error_text['en']))
        return

    caption = {
        'uz': 'Hisobot fayli tayyor',
        'ru': 'Файл отчёта готов',
        'en': 'Report file is ready',
    }

    await chat_message.answer_document(
        BufferedInputFile(file=file_bytes, filename=filename),
        caption=caption.get(lang, caption['en']),
    )


@router.message(Command('reports'))
@router.message(F.text.in_([get_text('btn_reports', 'uz'), get_text('btn_reports', 'ru'), get_text('btn_reports', 'en')]))
async def cmd_reports(message: Message):
    user = await _load_user(message)
    lang = _normalize_lang(user.language_code)

    parts = (message.text or '').strip().split()
    period = _resolve_period_from_token(parts[1] if len(parts) > 1 else None)

    if period:
        await _send_period_report(message, user.id, lang, period)
        return

    choose_text = {
        'uz': 'Hisobot davrini tanlang:',
        'ru': '\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u0435\u0440\u0438\u043e\u0434 \u043e\u0442\u0447\u0451\u0442\u0430:',
        'en': 'Choose report period:',
    }
    await message.answer(
        choose_text.get(lang, choose_text['en']),
        reply_markup=get_report_period_keyboard(lang),
    )


@router.callback_query(F.data.in_({'report_daily', 'report_weekly', 'report_monthly', 'report_yearly'}))
async def callback_reports_period(callback: CallbackQuery):
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        language_code=callback.from_user.language_code,
    )
    lang = _normalize_lang(user.language_code)

    period = _resolve_period_from_token(callback.data.replace('report_', '') if callback.data else None)
    if not period:
        await callback.answer('Invalid period', show_alert=True)
        return

    await callback.answer()
    await _send_period_report(callback.message, user.id, lang, period)
