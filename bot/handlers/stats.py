"""Balance and statistics handlers."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services.finance import get_or_create_user, get_user_balance, get_user_statistics
from config.i18n import get_text

router = Router()


async def _load_user(message: Message):
    return await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
    )


@router.message(Command('balance'))
@router.message(F.text.in_([get_text('btn_balance', 'uz'), get_text('btn_balance', 'ru'), get_text('btn_balance', 'en')]))
async def show_balance(message: Message):
    user = await _load_user(message)
    lang = user.language_code

    balance = await get_user_balance(user.id)
    text_map = {
        'uz': (
            f"💰 <b>Balansingiz</b>\n\n"
            f"💵 Umumiy: <b>{balance['total_balance']:,.2f} {balance['currency']}</b>\n"
            f"├─ O'z mablag'i: {balance['own_balance']:,.2f} {balance['currency']}\n"
            f"└─ Qabul qilingan: {balance['received_balance']:,.2f} {balance['currency']}"
        ),
        'ru': (
            f"💰 <b>Ваш баланс</b>\n\n"
            f"💵 Общий: <b>{balance['total_balance']:,.2f} {balance['currency']}</b>\n"
            f"├─ Свои средства: {balance['own_balance']:,.2f} {balance['currency']}\n"
            f"└─ Полученные переводы: {balance['received_balance']:,.2f} {balance['currency']}"
        ),
        'en': (
            f"💰 <b>Your balance</b>\n\n"
            f"💵 Total: <b>{balance['total_balance']:,.2f} {balance['currency']}</b>\n"
            f"├─ Own funds: {balance['own_balance']:,.2f} {balance['currency']}\n"
            f"└─ Received transfers: {balance['received_balance']:,.2f} {balance['currency']}"
        ),
    }

    await message.answer(text_map.get(lang, text_map['uz']), parse_mode='HTML')


@router.message(Command('stats'))
@router.message(F.text.in_([get_text('btn_stats', 'uz'), get_text('btn_stats', 'ru'), get_text('btn_stats', 'en')]))
async def show_stats(message: Message):
    user = await _load_user(message)
    lang = user.language_code

    stats = await get_user_statistics(user.id, period='month')

    if stats['difference'] > 0:
        diff = f"+{stats['difference']:,.2f}"
    elif stats['difference'] < 0:
        diff = f"{stats['difference']:,.2f}"
    else:
        diff = '0.00'

    top_rows = '\n'.join(
        [
            f"{idx + 1}. {cat['icon']} {cat['name']} - {cat['amount']:,.2f} {stats['currency']} ({cat['percent']:.1f}%)"
            for idx, cat in enumerate(stats['top_categories'])
        ]
    )
    if not top_rows:
        top_rows = '-'

    text_map = {
        'uz': (
            f"📊 <b>Statistika</b>\n\n"
            f"📅 Davr: {stats['period']}\n\n"
            f"📈 Daromad: <b>+{stats['total_income']:,.2f} {stats['currency']}</b>\n"
            f"📉 Xarajat: <b>-{stats['total_expense']:,.2f} {stats['currency']}</b>\n"
            f"➖ Farq: <b>{diff} {stats['currency']}</b>\n\n"
            f"🔝 Top kategoriyalar:\n{top_rows}\n\n"
            f"📤 Yuborilgan o'tkazmalar: {stats['transfers_sent']:,.2f} {stats['currency']} ({stats['transfers_sent_count']} ta)\n"
            f"📥 Qabul qilingan o'tkazmalar: {stats['transfers_received']:,.2f} {stats['currency']} ({stats['transfers_received_count']} ta)"
        ),
        'ru': (
            f"📊 <b>Статистика</b>\n\n"
            f"📅 Период: {stats['period']}\n\n"
            f"📈 Доходы: <b>+{stats['total_income']:,.2f} {stats['currency']}</b>\n"
            f"📉 Расходы: <b>-{stats['total_expense']:,.2f} {stats['currency']}</b>\n"
            f"➖ Разница: <b>{diff} {stats['currency']}</b>\n\n"
            f"🔝 Топ категории:\n{top_rows}\n\n"
            f"📤 Отправлено переводов: {stats['transfers_sent']:,.2f} {stats['currency']} ({stats['transfers_sent_count']})\n"
            f"📥 Получено переводов: {stats['transfers_received']:,.2f} {stats['currency']} ({stats['transfers_received_count']})"
        ),
        'en': (
            f"📊 <b>Statistics</b>\n\n"
            f"📅 Period: {stats['period']}\n\n"
            f"📈 Income: <b>+{stats['total_income']:,.2f} {stats['currency']}</b>\n"
            f"📉 Expense: <b>-{stats['total_expense']:,.2f} {stats['currency']}</b>\n"
            f"➖ Difference: <b>{diff} {stats['currency']}</b>\n\n"
            f"🔝 Top categories:\n{top_rows}\n\n"
            f"📤 Sent transfers: {stats['transfers_sent']:,.2f} {stats['currency']} ({stats['transfers_sent_count']})\n"
            f"📥 Received transfers: {stats['transfers_received']:,.2f} {stats['currency']} ({stats['transfers_received_count']})"
        ),
    }

    await message.answer(text_map.get(lang, text_map['uz']), parse_mode='HTML')
