from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.routers.groups import get_group_user_overview
from api.routers.workers import WorkerMoneyRequest, _create_worker_money_record, _require_workers_access
from database.category_labels import present_category_name
from database.finance import apply_debt_repayment, calculate_available_debt_source_native, normalize_debt_kind
from database.group_context import normalize_group_role, normalize_lang, normalize_theme
from database.workers import attendance_units, calculate_worker_period_summary


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


def test_cash_loan_available_balance_uses_remaining_and_unspent_amount():
    cash_loan = SimpleNamespace(
        status="active",
        kind="cash_loan",
        amount=Decimal("100"),
        used_amount=Decimal("40"),
        remaining_amount=Decimal("80"),
    )
    fully_spent = SimpleNamespace(
        status="active",
        kind="cash_loan",
        amount=Decimal("100"),
        used_amount=Decimal("100"),
        remaining_amount=Decimal("100"),
    )
    credit_purchase = SimpleNamespace(
        status="active",
        kind="credit_purchase",
        amount=Decimal("100"),
        used_amount=Decimal("0"),
        remaining_amount=Decimal("100"),
    )

    assert calculate_available_debt_source_native(cash_loan) == Decimal("60.00")
    assert calculate_available_debt_source_native(fully_spent) == Decimal("0.00")
    assert calculate_available_debt_source_native(credit_purchase) == Decimal("0.00")


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


@pytest.mark.asyncio
async def test_monthly_worker_summary_uses_full_salary_for_active_month(monkeypatch):
    class DummyScalarResult:
        def __init__(self, items):
            self.items = items

        def scalars(self):
            return self

        def all(self):
            return self.items

    class DummyDb:
        def __init__(self):
            self.calls = 0

        async def execute(self, _query):
            self.calls += 1
            if self.calls == 1:
                attendance = [
                    SimpleNamespace(status="present", units=Decimal("0")),
                    SimpleNamespace(status="half_day", units=Decimal("0")),
                    SimpleNamespace(status="absent", units=Decimal("0")),
                ]
                return DummyScalarResult(attendance)
            if self.calls == 2:
                return DummyScalarResult([SimpleNamespace(amount=Decimal("50"))])
            return DummyScalarResult([])

    async def fake_convert_amount(_db, amount, _source, _target):
        return Decimal(str(amount))

    monkeypatch.setattr("database.workers.convert_amount", fake_convert_amount)

    summary = await calculate_worker_period_summary(
        DummyDb(),
        worker=SimpleNamespace(
            id="worker-1",
            group_id=1,
            full_name="Ali",
            role_name="Builder",
            payment_type="monthly",
            rate=Decimal("600"),
            currency="USD",
            start_date=date(2026, 3, 24),
        ),
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        target_currency="USD",
    )

    assert summary["base_amount"] == 600.0
    assert summary["advance_amount"] == 50.0
    assert summary["payable_amount"] == 550.0
    assert summary["quantity"] == 1.0
    assert summary["attendance_count"] == 3
    assert summary["present_count"] == 1.0
    assert summary["half_day_count"] == 1.0
    assert summary["absent_count"] == 1.0


def test_system_categories_are_localized_by_language():
    assert present_category_name("Food", "uz", True) == "Oziq-ovqat"
    assert present_category_name("Еда и продукты", "en", True) == "Food"
    assert present_category_name("Transport", "ru", True) == "Транспорт"
    assert present_category_name("Custom farm", "ru", False) == "Custom farm"


@pytest.mark.asyncio
async def test_apply_debt_repayment_rejects_amount_above_remaining():
    class DummyDb:
        def add(self, _item):
            return None

        async def flush(self):
            return None

    debt = SimpleNamespace(
        id="debt-1",
        group_id=1,
        currency="USD",
        remaining_amount=Decimal("40"),
        amount=Decimal("100"),
        archived_at=None,
        paid_at=None,
        status="active",
    )
    user = SimpleNamespace(id=1, default_currency="USD")

    with pytest.raises(ValueError, match="exceeds the remaining debt"):
        await apply_debt_repayment(
            DummyDb(),
            debt=debt,
            user=user,
            amount=Decimal("50"),
            currency="USD",
            note=None,
        )


@pytest.mark.asyncio
async def test_worker_payment_rejects_amount_above_payable(monkeypatch):
    class DummyDb:
        def add(self, _item):
            return None

        async def commit(self):
            return None

    async def fake_main_balance(*_args, **_kwargs):
        return Decimal("500")

    async def fake_worker_summary(*_args, **_kwargs):
        return {"payable_amount": 40}

    monkeypatch.setattr("api.routers.workers.get_spendable_main_balance", fake_main_balance)
    monkeypatch.setattr("api.routers.workers.calculate_worker_period_summary", fake_worker_summary)

    with pytest.raises(HTTPException, match="Maximum|Максимум"):
        await _create_worker_money_record(
            db=DummyDb(),
            current_user=SimpleNamespace(id=1, language_code="en", default_currency="USD"),
            worker=SimpleNamespace(id="worker-1", group_id=1, full_name="Ali"),
            payload=WorkerMoneyRequest(amount=Decimal("50"), currency="USD", payment_date=date(2026, 3, 24), note=None),
            record_type="payment",
        )


@pytest.mark.asyncio
async def test_workers_permission_requires_group_membership(monkeypatch):
    async def fake_has_group_access(*_args, **_kwargs):
        return False

    monkeypatch.setattr("api.routers.workers.user_has_group_access", fake_has_group_access)

    with pytest.raises(HTTPException, match="Access denied|Доступ запрещён"):
        await _require_workers_access(
            db=SimpleNamespace(),
            current_user=SimpleNamespace(id=1, language_code="en"),
            group_id=1,
        )


@pytest.mark.asyncio
async def test_group_overview_uses_viewer_currency(monkeypatch):
    class DummyResult:
        def __init__(self, value):
            self.value = value

        def all(self):
            return self.value

        def scalars(self):
            return self

        def all(self):
            return self.value

    class DummyDb:
        def __init__(self):
            self.calls = 0

        async def execute(self, _query):
            self.calls += 1
            if self.calls == 1:
                membership = SimpleNamespace(role="member")
                user = SimpleNamespace(id=10, username="ali", first_name="Ali", last_name="Valiyev")
                return DummyResult([(membership, user)])
            if self.calls == 2:
                tx = SimpleNamespace(
                    id="tx-1",
                    type=SimpleNamespace(value="income"),
                    amount=Decimal("184500"),
                    currency="UZS",
                    description="Demo income",
                    transaction_date=date(2026, 3, 24),
                )
                return DummyResult([tx])
            return DummyResult([SimpleNamespace(status="active")])

    async def fake_is_group_admin(*_args, **_kwargs):
        return True

    async def fake_get_user_balance_summary(_db, _user, target_currency=None, group_id=None):
        assert target_currency == "USD"
        assert group_id == 1
        return {
            "currency": "USD",
            "total_balance": Decimal("15"),
            "debt_balance": Decimal("45"),
            "outstanding_debt_balance": Decimal("50"),
        }

    async def fake_convert_amount(_db, amount, source_currency, target_currency):
        assert amount == Decimal("184500")
        assert source_currency == "UZS"
        assert target_currency == "USD"
        return Decimal("15")

    async def fake_check_user_admin_status(*_args, **_kwargs):
        return False

    monkeypatch.setattr("api.routers.groups.is_group_admin", fake_is_group_admin)
    monkeypatch.setattr("api.routers.groups.check_user_admin_status", fake_check_user_admin_status)
    monkeypatch.setattr("api.routers.groups.get_user_balance_summary", fake_get_user_balance_summary)
    monkeypatch.setattr("api.routers.groups.convert_amount", fake_convert_amount)

    result = await get_group_user_overview(
        1,
        current_user=SimpleNamespace(language_code="en", default_currency="USD"),
        db=DummyDb(),
    )

    assert result[0]["currency"] == "USD"
    assert result[0]["total_balance"] == 15.0
    assert result[0]["recent_transactions"][0]["currency"] == "USD"
    assert result[0]["recent_transactions"][0]["amount"] == 15.0
