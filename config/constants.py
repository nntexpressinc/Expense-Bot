"""
Application constants
"""

# Transaction types
TRANSACTION_TYPE_INCOME = "income"
TRANSACTION_TYPE_EXPENSE = "expense"
TRANSACTION_TYPE_TRANSFER_OUT = "transfer_out"
TRANSACTION_TYPE_TRANSFER_IN = "transfer_in"

# Transfer statuses
TRANSFER_STATUS_PENDING = "pending"
TRANSFER_STATUS_COMPLETED = "completed"
TRANSFER_STATUS_CANCELLED = "cancelled"

# Category types
CATEGORY_TYPE_INCOME = "income"
CATEGORY_TYPE_EXPENSE = "expense"

# Notification types
NOTIFICATION_TYPE_DAILY_REMINDER = "daily_reminder"
NOTIFICATION_TYPE_TRANSFER_RECEIVED = "transfer_received"
NOTIFICATION_TYPE_TRANSFER_SPENT = "transfer_spent"
NOTIFICATION_TYPE_BUDGET_WARNING = "budget_warning"

# Report types
REPORT_TYPE_DAILY = "daily"
REPORT_TYPE_WEEKLY = "weekly"
REPORT_TYPE_MONTHLY = "monthly"
REPORT_TYPE_CUSTOM = "custom"

# Report formats
REPORT_FORMAT_PDF = "pdf"
REPORT_FORMAT_EXCEL = "excel"

# Currencies
DEFAULT_CURRENCY = "UZS"
SUPPORTED_CURRENCIES = ["UZS", "USD"]
DEFAULT_EXCHANGE_RATE = 12300  # USD to UZS

# Validation
MIN_TRANSACTION_AMOUNT = 0.01
MAX_TRANSACTION_AMOUNT = 1_000_000_000
MAX_TRANSFER_AMOUNT = 1_000_000_000

# Button texts (Russian)
BTN_ADD_INCOME = "➕ Доход"
BTN_ADD_EXPENSE = "➖ Расход"
BTN_TRANSFER = "💸 Перевод"
BTN_STATS = "📊 Статистика"
BTN_BALANCE = "💰 Баланс"
BTN_REPORTS = "📄 Отчёты"
BTN_SETTINGS = "⚙️ Настройки"
BTN_HELP = "❓ Помощь"
BTN_CANCEL = "❌ Отмена"
BTN_SKIP = "⏭️ Пропустить"
BTN_BACK = "◀️ Назад"
BTN_CONFIRM = "✅ Подтвердить"
BTN_REJECT = "❌ Отклонить"

# Messages
MSG_WELCOME = """
👋 Добро пожаловать в Expenses Bot!

Я помогу вам контролировать доходы и расходы, а также отслеживать, 
как другие люди тратят переданные вами средства.

🔹 Добавляйте доходы и расходы
🔹 Переводите деньги другим пользователям
🔹 Отслеживайте расходы получателей
🔹 Получайте подробную статистику

Используйте меню ниже для начала работы.
"""

MSG_HELP = """
📖 Справка по командам:

💰 Финансовые операции:
/income - Добавить доход
/expense - Добавить расход
/balance - Показать баланс
/stats - Статистика и отчёты

💸 Переводы:
/transfer - Перевести деньги
/transfers - Мои переводы
/received - Полученные переводы

⚙️ Настройки:
/settings - Настройки приложения
/currency - Изменить валюту
/language - Изменить язык

ℹ️ Прочее:
/start - Главное меню
/help - Эта справка
/menu - Вернуться в главное меню
/cancel - Отменить текущую операцию

💡 Используйте кнопки меню для быстрого доступа!
"""

# Limits
MAX_DESCRIPTION_LENGTH = 500
MAX_CATEGORY_NAME_LENGTH = 100
MAX_TRANSACTIONS_PER_PAGE = 10
MAX_CATEGORIES_PER_USER = 50

# Date formats
DATE_FORMAT = "%d.%m.%Y"
DATETIME_FORMAT = "%d.%m.%Y %H:%M"
TIME_FORMAT = "%H:%M"

# Redis keys prefixes
REDIS_KEY_USER_STATE = "user_state:{user_id}"
REDIS_KEY_TRANSFER_PENDING = "transfer_pending:{transfer_id}"
REDIS_KEY_RATE_LIMIT = "rate_limit:{user_id}"
REDIS_KEY_CACHE_BALANCE = "cache_balance:{user_id}"

# Cache TTL (seconds)
CACHE_TTL_SHORT = 60  # 1 minute
CACHE_TTL_MEDIUM = 300  # 5 minutes
CACHE_TTL_LONG = 3600  # 1 hour

# Emojis
EMOJI_MONEY = "💰"
EMOJI_INCOME = "📈"
EMOJI_EXPENSE = "📉"
EMOJI_TRANSFER = "💸"
EMOJI_BALANCE = "💵"
EMOJI_STATS = "📊"
EMOJI_REPORT = "📄"
EMOJI_SETTINGS = "⚙️"
EMOJI_SUCCESS = "✅"
EMOJI_ERROR = "❌"
EMOJI_WARNING = "⚠️"
EMOJI_INFO = "ℹ️"
EMOJI_LOADING = "⏳"
