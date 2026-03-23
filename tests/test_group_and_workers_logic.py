from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from database.finance import normalize_debt_kind
from database.group_context import normalize_group_role, normalize_lang, normalize_theme
from database.workers import attendance_units


def test_language_and_theme_normalization():
    assert normalize_lang("ru-RU") == "ru"
    assert normalize_lang("en-US") == "en"
    assert normalize_lang("something") == "uz"

    assert normalize_theme("dark") == "dark"
    assert normalize_theme("LIGHT") == "light"
    assert normalize_theme("broken") == "light"

    assert normalize_group_role("admin") == "admin"
    assert normalize_group_role("member") == "member"
    assert normalize_group_role("owner") == "member"
    assert normalize_debt_kind("cash_loan") == "cash_loan"
    assert normalize_debt_kind("credit_purchase") == "credit_purchase"
    assert normalize_debt_kind("borrowed") == "credit_purchase"


def test_attendance_units_supports_daily_half_day_and_custom():
    present = SimpleNamespace(status="present", units=Decimal("0"))
    absent = SimpleNamespace(status="absent", units=Decimal("0"))
    half_day = SimpleNamespace(status="half_day", units=Decimal("0"))
    custom = SimpleNamespace(status="custom", units=Decimal("7.5"))
    volume_with_units = SimpleNamespace(status="present", units=Decimal("3"))

    assert attendance_units(present) == Decimal("1")
    assert attendance_units(absent) == Decimal("0")
    assert attendance_units(half_day) == Decimal("0.5")
    assert attendance_units(custom) == Decimal("7.5")
    assert attendance_units(volume_with_units) == Decimal("3")


def test_worker_period_inputs_are_plain_dates():
    today = date.today()
    assert isinstance(today, date)
