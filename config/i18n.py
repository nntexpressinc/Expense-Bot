"""Multi-language support for Expenses Bot."""

from typing import Dict

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'btn_add_income': {'uz': '➕ Daromad', 'ru': '➕ Доход', 'en': '➕ Income'},
    'btn_add_expense': {'uz': '➖ Xarajat', 'ru': '➖ Расход', 'en': '➖ Expense'},
    'btn_transfer': {'uz': "💸 O'tkazma", 'ru': '💸 Перевод', 'en': '💸 Transfer'},
    'btn_stats': {'uz': '📊 Statistika', 'ru': '📊 Статистика', 'en': '📊 Statistics'},
    'btn_balance': {'uz': '💰 Balans', 'ru': '💰 Баланс', 'en': '💰 Balance'},
    'btn_reports': {'uz': '📄 Hisobotlar', 'ru': '📄 Отчёты', 'en': '📄 Reports'},
    'btn_settings': {'uz': '⚙️ Sozlamalar', 'ru': '⚙️ Настройки', 'en': '⚙️ Settings'},
    'btn_switch_group': {'uz': "🏢 Guruhni almashtirish", 'ru': '🏢 Сменить группу', 'en': '🏢 Switch group'},
    'btn_invite': {'uz': "🔗 Guruhga qo'shish", 'ru': '🔗 Пригласить в группу', 'en': '🔗 Invite to group'},
    'btn_debts': {'uz': '💳 Qarzlar', 'ru': '💳 Долги', 'en': '💳 Debts'},
    'msg_debt_enter_amount': {
        'uz': "Qarz summasi va valyutasini kiriting. Masalan: 100000 yoki 10 USD. Default: {currency}",
        'ru': "Введите сумму долга. Пример: 100000 или 10 USD. По умолчанию: {currency}",
        'en': "Enter debt amount. Example: 100000 or 10 USD. Default: {currency}",
    },
    'msg_debt_enter_description': {
        'uz': "Izoh kiriting yoki bo'sh qoldiring.",
        'ru': "Введите описание или оставьте пустым.",
        'en': "Enter description or leave empty.",
    },
    'msg_debt_added': {
        'uz': "✅ Qarz qo'shildi",
        'ru': "✅ Долг добавлен",
        'en': "✅ Debt added",
    },
    'msg_debt_pay_prompt': {
        'uz': "To'lov summasini kiriting. Masalan: 50000 yoki 10 USD. Default: {currency}",
        'ru': "Введите сумму погашения. Пример: 50000 или 10 USD. По умолчанию: {currency}",
        'en': "Enter payment amount. Example: 50000 or 10 USD. Default: {currency}",
    },
    'err_invalid_amount': {
        'uz': "❌ Noto'g'ri summa",
        'ru': "❌ Неверная сумма",
        'en': "❌ Invalid amount",
    },
    'btn_help': {'uz': '❓ Yordam', 'ru': '❓ Помощь', 'en': '❓ Help'},
    'btn_cancel': {'uz': '❌ Bekor qilish', 'ru': '❌ Отмена', 'en': '❌ Cancel'},
    'btn_skip': {'uz': "⏭️ O'tkazib yuborish", 'ru': '⏭️ Пропустить', 'en': '⏭️ Skip'},
    'btn_back': {'uz': '◀️ Orqaga', 'ru': '◀️ Назад', 'en': '◀️ Back'},
    'btn_confirm': {'uz': '✅ Tasdiqlash', 'ru': '✅ Подтвердить', 'en': '✅ Confirm'},
    'btn_reject': {'uz': '❌ Rad etish', 'ru': '❌ Отклонить', 'en': '❌ Reject'},
    'btn_open_miniapp': {'uz': "📱 Mini App ochish", 'ru': '📱 Открыть Mini App', 'en': '📱 Open Mini App'},
    'msg_open_miniapp_prompt': {
        'uz': "Mini Appni ochish uchun quyidagi tugmani bosing.",
        'ru': 'Нажмите кнопку ниже, чтобы открыть Mini App.',
        'en': 'Press the button below to open the Mini App.',
    },
    'msg_open_miniapp_unavailable': {
        'uz': "Mini App URL sozlanmagan.",
        'ru': 'URL Mini App не настроен.',
        'en': 'Mini App URL is not configured.',
    },

    'msg_welcome': {
        'uz': (
            "👋 Expenses Bot'ga xush kelibsiz!\n\n"
            "Daromad/xarajatlarni boshqaring, o'tkazmalarni yuboring va mablag'lar sarfini kuzating."
        ),
        'ru': (
            '👋 Добро пожаловать в Expenses Bot!\n\n'
            'Управляйте доходами/расходами, переводами и контролируйте траты.'
        ),
        'en': (
            '👋 Welcome to Expenses Bot!\n\n'
            'Manage income/expenses, send transfers, and track spending.'
        ),
    },
    'msg_help': {
        'uz': (
            "📘 Buyruqlar:\n"
            '/income - Daromad\n'
            '/expense - Xarajat\n'
            '/balance - Balans\n'
            '/stats - Statistika\n'
            '/transfer - O\'tkazma\n'
            '/transfers - Yuborilgan\n'
            '/received - Qabul qilingan\n'
            '/group - Faol guruh\n'
            '/invite - Guruh linki\n'
            '/settings - Sozlamalar\n'
            '/users - Users (admin)\n'
            '/cancel - Bekor qilish'
        ),
        'ru': (
            '📘 Команды:\n'
            '/income - Доход\n'
            '/expense - Расход\n'
            '/balance - Баланс\n'
            '/stats - Статистика\n'
            '/transfer - Перевод\n'
            '/transfers - Отправленные\n'
            '/received - Полученные\n'
            '/group - Активная группа\n'
            '/invite - Ссылка группы\n'
            '/settings - Настройки\n'
            '/users - Пользователи (admin)\n'
            '/cancel - Отмена'
        ),
        'en': (
            '📘 Commands:\n'
            '/income - Income\n'
            '/expense - Expense\n'
            '/balance - Balance\n'
            '/stats - Statistics\n'
            '/transfer - Transfer\n'
            '/transfers - Sent\n'
            '/received - Received\n'
            '/group - Active group\n'
            '/invite - Group invite link\n'
            '/settings - Settings\n'
            '/users - Users (admin)\n'
            '/cancel - Cancel'
        ),
    },
    'msg_select_language': {'uz': 'Tilni tanlang:', 'ru': 'Выберите язык:', 'en': 'Select language:'},
    'msg_language_changed': {'uz': "Til o'zgartirildi ✅", 'ru': 'Язык изменён ✅', 'en': 'Language changed ✅'},
    'msg_select_currency': {'uz': 'Valyutani tanlang:', 'ru': 'Выберите валюту:', 'en': 'Select currency:'},
    'msg_currency_changed': {'uz': "Valyuta o'zgartirildi ✅", 'ru': 'Валюта изменена ✅', 'en': 'Currency changed ✅'},
    'msg_operation_cancelled': {'uz': 'Operatsiya bekor qilindi.', 'ru': 'Операция отменена.', 'en': 'Operation cancelled.'},
    'msg_main_menu': {'uz': 'Asosiy menyu:', 'ru': 'Главное меню:', 'en': 'Main menu:'},
    'msg_settings': {'uz': '⚙️ Sozlamalar', 'ru': '⚙️ Настройки', 'en': '⚙️ Settings'},
    'msg_active_group': {'uz': 'Faol guruh', 'ru': 'Активная группа', 'en': 'Active group'},
    'msg_select_group': {'uz': 'Guruhni tanlang:', 'ru': 'Выберите группу:', 'en': 'Select group:'},
    'msg_group_changed': {'uz': "Guruh o'zgartirildi ✅", 'ru': 'Группа изменена ✅', 'en': 'Group changed ✅'},
    'msg_only_one_group': {
        'uz': 'Sizda faqat bitta guruh bor.',
        'ru': 'У вас только одна группа.',
        'en': 'You only have one group.',
    },
    'msg_no_groups': {
        'uz': 'Siz hali hech qaysi guruhga ulanmagansiz.',
        'ru': 'Вы пока не подключены ни к одной группе.',
        'en': 'You are not connected to any group yet.',
    },
    'msg_admin_panel': {'uz': '👨‍💼 Admin panel', 'ru': '👨‍💼 Админ панель', 'en': '👨‍💼 Admin panel'},
    'msg_exchange_rate': {'uz': '💱 Valyuta kursi', 'ru': '💱 Курс валют', 'en': '💱 Exchange rate'},
    'msg_exchange_rate_updated': {'uz': 'Valyuta kursi yangilandi ✅', 'ru': 'Курс валют обновлён ✅', 'en': 'Exchange rate updated ✅'},
}


def get_text(key: str, lang: str = 'uz') -> str:
    data = TRANSLATIONS.get(key)
    if not data:
        return key
    language = (lang or 'uz').split('-')[0].lower()
    return data.get(language) or data.get('uz') or data.get('en') or key


def get_user_language(user) -> str:
    value = getattr(user, 'language_code', None)
    language = (value or 'uz').split('-')[0].lower()
    if language in {'uz', 'ru', 'en'}:
        return language
    return 'uz'
