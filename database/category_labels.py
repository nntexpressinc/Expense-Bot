from __future__ import annotations

import re


_LABELS = {
    "food": {"uz": "Oziq-ovqat", "ru": "Еда и продукты", "en": "Food"},
    "transport": {"uz": "Transport", "ru": "Транспорт", "en": "Transport"},
    "housing": {"uz": "Uy-joy", "ru": "Жильё", "en": "Housing"},
    "utilities": {"uz": "Kommunal xizmatlar", "ru": "Коммунальные услуги", "en": "Utilities"},
    "health": {"uz": "Sog'liq", "ru": "Здоровье", "en": "Health"},
    "cafe_restaurants": {"uz": "Kafe va restoran", "ru": "Кафе и рестораны", "en": "Cafe and restaurants"},
    "beauty": {"uz": "Go'zallik", "ru": "Красота", "en": "Beauty"},
    "education": {"uz": "Ta'lim", "ru": "Образование", "en": "Education"},
    "clothing": {"uz": "Kiyim", "ru": "Одежда", "en": "Clothing"},
    "gifts": {"uz": "Sovg'alar", "ru": "Подарки", "en": "Gifts"},
    "travel": {"uz": "Sayohat", "ru": "Путешествия", "en": "Travel"},
    "entertainment": {"uz": "Ko'ngilochar", "ru": "Развлечения", "en": "Entertainment"},
    "other": {"uz": "Boshqa", "ru": "Разное", "en": "Other"},
    "materials": {"uz": "Materiallar", "ru": "Материалы", "en": "Materials"},
    "communication": {"uz": "Aloqa", "ru": "Связь", "en": "Communication"},
    "sport": {"uz": "Sport", "ru": "Спорт", "en": "Sport"},
    "salary": {"uz": "Oylik", "ru": "Зарплата", "en": "Salary"},
    "freelance": {"uz": "Frilans", "ru": "Фриланс", "en": "Freelance"},
    "business": {"uz": "Biznes", "ru": "Бизнес", "en": "Business"},
    "investments": {"uz": "Investitsiya", "ru": "Инвестиции", "en": "Investments"},
    "sales": {"uz": "Savdo", "ru": "Продажи", "en": "Sales"},
    "transfer_in": {"uz": "Transfer qabul qilindi", "ru": "Полученный перевод", "en": "Transfer in"},
    "other_income": {"uz": "Boshqa kirim", "ru": "Прочий доход", "en": "Other income"},
    "debt_repayment": {"uz": "Qarz qaytarish", "ru": "Погашение долга", "en": "Debt repayment"},
    "debt_return": {"uz": "Qarz qaytdi", "ru": "Возврат долга", "en": "Debt return"},
    "other_expense": {"uz": "Boshqa chiqim", "ru": "Прочий расход", "en": "Other expense"},
}

_VARIANTS = {
    "food": ["food", "еда и продукты", "еда", "oziq ovqat", "ozik ovqat", "ovqat", "ovqatlar"],
    "transport": ["transport", "транспорт"],
    "housing": ["housing", "жильё", "жилье", "uy joy", "uy-joy"],
    "utilities": ["utilities", "коммунальные услуги", "kommunal xizmatlar"],
    "health": ["health", "здоровье", "sogliq", "sogliq"],
    "cafe_restaurants": ["cafe and restaurants", "cafe and restaurant", "кафе и рестораны", "kafe va restoran"],
    "beauty": ["beauty", "красота", "gozallik", "go'zallik"],
    "education": ["education", "образование", "talim", "ta'lim"],
    "clothing": ["clothing", "одежда", "kiyim"],
    "gifts": ["gifts", "подарки", "sovgalar"],
    "travel": ["travel", "путешествия", "sayohat"],
    "entertainment": ["entertainment", "развлечения", "kongilochar", "ko'ngilochar"],
    "other": ["other", "разное", "boshqa"],
    "materials": ["materials", "материалы", "materiallar"],
    "communication": ["communication", "связь", "aloqa"],
    "sport": ["sport", "спорт"],
    "salary": ["salary", "зарплата", "oylik"],
    "freelance": ["freelance", "фриланс", "frilans"],
    "business": ["business", "бизнес", "biznes"],
    "investments": ["investments", "инвестиции", "investitsiya"],
    "sales": ["sales", "продажи", "savdo"],
    "transfer_in": ["transfer in", "полученный перевод", "transfer qabul qilindi"],
    "other_income": ["other income", "прочий доход", "boshqa kirim"],
    "debt_repayment": ["debt repayment", "погашение долга", "qarz qaytarish"],
    "debt_return": ["debt return", "возврат долга", "qarz qaytdi"],
    "other_expense": ["other expense", "прочий расход", "boshqa chiqim"],
}


def _normalize(value: str) -> str:
    cleaned = (value or "").strip().lower().replace("ё", "е")
    cleaned = re.sub(r"[^a-zа-я0-9]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


_VARIANT_TO_KEY = {
    _normalize(variant): key
    for key, variants in _VARIANTS.items()
    for variant in variants
}


def translate_system_category_name(name: str, lang: str) -> str:
    key = _VARIANT_TO_KEY.get(_normalize(name))
    if not key:
        return name
    labels = _LABELS.get(key)
    return labels.get(lang, labels["uz"]) if labels else name


def present_category_name(name: str, lang: str, is_system: bool) -> str:
    if not is_system:
        return name
    return translate_system_category_name(name, lang)
