"""Keyboard builders for bot interface."""

from typing import List, Optional

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config.i18n import get_text


def get_main_menu_keyboard(lang: str = 'uz', miniapp_url: str = None) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    if miniapp_url:
        builder.row(
            KeyboardButton(
                text=get_text('btn_open_miniapp', lang),
                web_app=WebAppInfo(url=miniapp_url),
            )
        )

    builder.row(
        KeyboardButton(text=get_text('btn_add_income', lang)),
        KeyboardButton(text=get_text('btn_add_expense', lang)),
    )
    builder.row(
        KeyboardButton(text=get_text('btn_transfer', lang)),
        KeyboardButton(text=get_text('btn_stats', lang)),
    )
    builder.row(
        KeyboardButton(text=get_text('btn_balance', lang)),
        KeyboardButton(text=get_text('btn_reports', lang)),
    )
    builder.row(KeyboardButton(text=get_text('btn_debts', lang)))
    builder.row(
        KeyboardButton(text=get_text('btn_settings', lang)),
        KeyboardButton(text=get_text('btn_help', lang)),
    )
    builder.row(KeyboardButton(text=get_text('btn_invite', lang)))

    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard(lang: str = 'uz') -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('btn_cancel', lang)))
    return builder.as_markup(resize_keyboard=True)


def get_skip_cancel_keyboard(lang: str = 'uz') -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=get_text('btn_skip', lang)),
        KeyboardButton(text=get_text('btn_cancel', lang)),
    )
    return builder.as_markup(resize_keyboard=True)


def get_language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data='lang_uz'),
        InlineKeyboardButton(text='🇷🇺 Русский', callback_data='lang_ru'),
    )
    builder.row(InlineKeyboardButton(text='🇬🇧 English', callback_data='lang_en'))
    return builder.as_markup()


def get_currency_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇺🇿 UZS (So'm)", callback_data='currency_UZS'),
        InlineKeyboardButton(text='🇺🇸 USD (Dollar)', callback_data='currency_USD'),
    )
    return builder.as_markup()


def get_settings_keyboard(lang: str = 'uz', is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"🌐 {get_text('msg_select_language', lang)}", callback_data='settings_language')
    )
    builder.row(
        InlineKeyboardButton(text=f"💱 {get_text('msg_select_currency', lang)}", callback_data='settings_currency')
    )

    if is_admin:
        builder.row(
            InlineKeyboardButton(text=get_text('msg_admin_panel', lang), callback_data='admin_panel')
        )

    return builder.as_markup()


def get_admin_keyboard(lang: str = 'uz') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text('msg_exchange_rate', lang), callback_data='admin_exchange_rate')
    )
    builder.row(
        InlineKeyboardButton(text=get_text('btn_back', lang), callback_data='settings_menu')
    )
    return builder.as_markup()


def get_categories_keyboard(
    categories: List[dict], row_width: int = 2, lang: str = 'uz'
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for category in categories:
        builder.add(
            InlineKeyboardButton(
                text=f"{category.get('icon', '')} {category['name']}",
                callback_data=f"category_{category['id']}",
            )
        )

    builder.adjust(row_width)
    builder.row(InlineKeyboardButton(text=get_text('btn_cancel', lang), callback_data='cancel'))
    return builder.as_markup()


def get_confirmation_keyboard(
    confirm_callback: str, cancel_callback: str = 'cancel', lang: str = 'uz'
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text('btn_confirm', lang), callback_data=confirm_callback),
        InlineKeyboardButton(text=get_text('btn_reject', lang), callback_data=cancel_callback),
    )
    return builder.as_markup()


def get_transfers_list_keyboard(transfers: List[dict], lang: str = 'uz') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    remaining_text = {'uz': 'qoldi', 'ru': 'остаток', 'en': 'remaining'}.get(lang, 'qoldi')

    for transfer in transfers:
        text = f"{transfer['name']} - {transfer['amount']} {transfer['currency']}"
        if 'remaining' in transfer:
            text += f" ({remaining_text}: {transfer['remaining']})"
        builder.add(
            InlineKeyboardButton(text=text, callback_data=f"transfer_{transfer['id']}")
        )

    builder.adjust(1)
    builder.row(InlineKeyboardButton(text=get_text('btn_back', lang), callback_data='back'))
    return builder.as_markup()


def get_transfer_details_keyboard(transfer_id: str, lang: str = 'uz') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    history_text = {'uz': '🧾 Xarajatlar tarixi', 'ru': '🧾 История расходов', 'en': '🧾 Expense history'}.get(lang)
    report_text = {'uz': '📊 Hisobot', 'ru': '📊 Отчёт', 'en': '📊 Report'}.get(lang)
    notif_text = {'uz': '🔔 Bildirishnomalar', 'ru': '🔔 Уведомления', 'en': '🔔 Notifications'}.get(lang)
    cancel_text = {'uz': "❌ O'tkazmani bekor qilish", 'ru': '❌ Отменить перевод', 'en': '❌ Cancel transfer'}.get(lang)

    builder.row(InlineKeyboardButton(text=history_text, callback_data=f'transfer_history_{transfer_id}'))
    builder.row(InlineKeyboardButton(text=report_text, callback_data=f'transfer_report_{transfer_id}'))
    builder.row(InlineKeyboardButton(text=notif_text, callback_data=f'transfer_notifications_{transfer_id}'))
    builder.row(InlineKeyboardButton(text=cancel_text, callback_data=f'transfer_cancel_{transfer_id}'))
    builder.row(InlineKeyboardButton(text=get_text('btn_back', lang), callback_data='transfers_list'))

    return builder.as_markup()


def get_report_period_keyboard(lang: str = 'uz') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    labels = {
        'uz': ('📅 Kun', '📅 Hafta', '📅 Oy', '📅 Yil'),
        'ru': ('📅 День', '📅 Неделя', '📅 Месяц', '📅 Год'),
        'en': ('📅 Day', '📅 Week', '📅 Month', '📅 Year'),
    }.get(lang, ('📅 Kun', '📅 Hafta', '📅 Oy', '📅 Yil'))

    builder.row(
        InlineKeyboardButton(text=labels[0], callback_data='report_daily'),
        InlineKeyboardButton(text=labels[1], callback_data='report_weekly'),
    )
    builder.row(
        InlineKeyboardButton(text=labels[2], callback_data='report_monthly'),
        InlineKeyboardButton(text=labels[3], callback_data='report_yearly'),
    )
    builder.row(InlineKeyboardButton(text=get_text('btn_cancel', lang), callback_data='cancel'))
    return builder.as_markup()


def get_report_format_keyboard(lang: str = 'uz') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text='📊 Excel', callback_data='format_excel'),
        InlineKeyboardButton(text='📄 PDF', callback_data='format_pdf'),
    )
    builder.row(InlineKeyboardButton(text=get_text('btn_cancel', lang), callback_data='cancel'))
    return builder.as_markup()


def get_admin_users_keyboard(users: list[dict], lang: str = 'uz') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user in users:
        label = f"{'🛡' if user.get('is_admin') else '👤'} "
        full_name = f"{user.get('first_name') or ''} {user.get('last_name') or ''}".strip()
        label += full_name or (f"@{user['username']}" if user.get('username') else str(user['id']))
        builder.add(InlineKeyboardButton(text=label[:32], callback_data=f"admin_user_{user['id']}"))
    if users:
        builder.adjust(1)
    builder.row(InlineKeyboardButton(text=get_text('btn_back', lang), callback_data='admin_menu'))
    return builder.as_markup()


def get_admin_user_actions_keyboard(user_id: int, is_admin: bool, lang: str = 'uz') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_label = {'uz': 'Rolni almashtirish', 'ru': 'Переключить роль', 'en': 'Toggle role'}.get(lang, 'Toggle role')
    reset_label = {'uz': 'Balansni 0 qilish', 'ru': 'Обнулить баланс', 'en': 'Reset balance'}.get(lang, 'Reset balance')
    set_label = {'uz': 'Balansni o‘rnatish', 'ru': 'Задать баланс', 'en': 'Set balance'}.get(lang, 'Set balance')
    delete_label = {'uz': 'O‘chirish', 'ru': 'Удалить', 'en': 'Delete'}.get(lang, 'Delete')

    builder.row(
        InlineKeyboardButton(
            text=f"{'🛡' if is_admin else '👤'} {toggle_label}",
            callback_data=f"admin_user_role_{user_id}_{1 if is_admin else 0}",
        )
    )
    builder.row(
        InlineKeyboardButton(text=f"♻️ {reset_label}", callback_data=f"admin_user_reset_{user_id}"),
        InlineKeyboardButton(text=f"✏️ {set_label}", callback_data=f"admin_user_set_{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text=f"🗑 {delete_label}", callback_data=f"admin_user_delete_{user_id}"),
    )
    builder.row(InlineKeyboardButton(text=get_text('btn_back', lang), callback_data='admin_users'))
    return builder.as_markup()


def get_admin_user_delete_confirm_keyboard(user_id: int, lang: str = 'uz') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    yes = {'uz': 'Ha', 'ru': 'Да', 'en': 'Yes'}.get(lang, 'Yes')
    no = {'uz': 'Yo‘q', 'ru': 'Нет', 'en': 'No'}.get(lang, 'No')
    builder.row(
        InlineKeyboardButton(text=f"✅ {yes}", callback_data=f"admin_user_delete_confirm_{user_id}"),
        InlineKeyboardButton(text=f"❌ {no}", callback_data=f"admin_user_{user_id}"),
    )
    return builder.as_markup()


def get_transfer_recipients_keyboard(users: list[dict], lang: str = 'uz') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user in users:
        if user.get('username'):
            label = f"@{user['username']}"
        else:
            name = f"{user.get('first_name') or ''} {user.get('last_name') or ''}".strip() or str(user['id'])
            label = name
        builder.add(
            InlineKeyboardButton(
                text=label[:32],
                callback_data=f"transfer_recipient_{user['id']}",
            )
        )
    if users:
        builder.adjust(2)
    builder.row(
        InlineKeyboardButton(
            text={'uz': '🔄 Yangilash', 'ru': '🔄 Обновить', 'en': '🔄 Refresh'}.get(lang, 'Refresh'),
            callback_data='transfer_recipients_refresh',
        )
    )
    builder.row(InlineKeyboardButton(text=get_text('btn_cancel', lang), callback_data='cancel'))
    return builder.as_markup()


def get_transfer_start_keyboard(lang: str = 'uz') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text={'uz': "👥 Foydalanuvchilar ro'yxati", 'ru': '👥 Список пользователей', 'en': '👥 Users list'}.get(
                lang, 'Users'
            ),
            callback_data='transfer_recipients_list',
        )
    )
    builder.row(InlineKeyboardButton(text=get_text('btn_cancel', lang), callback_data='cancel'))
    return builder.as_markup()


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str,
    lang: str = 'uz',
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    buttons = []
    if current_page > 0:
        buttons.append(
            InlineKeyboardButton(
                text='◀️',
                callback_data=f'{callback_prefix}_{current_page - 1}',
            )
        )

    buttons.append(
        InlineKeyboardButton(text=f'{current_page + 1}/{total_pages}', callback_data='page_info')
    )

    if current_page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(
                text='▶️',
                callback_data=f'{callback_prefix}_{current_page + 1}',
            )
        )

    builder.row(*buttons)
    builder.row(InlineKeyboardButton(text=get_text('btn_back', lang), callback_data='back'))
    return builder.as_markup()
