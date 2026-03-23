from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.constants import DEFAULT_EXCHANGE_RATE
from database.group_context import get_active_group_id
from database.models import (
    Debt,
    DebtRepayment,
    DebtUsage,
    ExchangeRate,
    Transaction,
    TransactionType,
    Transfer,
    TransferExpense,
    TransferStatus,
    User,
)

SUPPORTED_APP_CURRENCIES = {"UZS", "USD"}
MONEY_QUANT = Decimal("0.01")


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def normalize_currency(currency: str | None, fallback: str = "UZS") -> str:
    value = (currency or fallback).upper()
    return value if value in SUPPORTED_APP_CURRENCIES else fallback


def normalize_funding_source(source: str | None) -> str:
    value = (source or "main").lower()
    return value if value in {"main", "debt"} else "main"


def _fx_cache(db: AsyncSession) -> dict[tuple[str, str], Decimal]:
    cache = db.info.get("_fx_cache")
    if cache is None:
        cache = {}
        db.info["_fx_cache"] = cache
    return cache


async def _ensure_default_usd_uzs_rates(db: AsyncSession) -> None:
    usd_to_uzs = Decimal(str(DEFAULT_EXCHANGE_RATE))
    uzs_to_usd = Decimal("1") / usd_to_uzs

    for from_curr, to_curr, rate in (
        ("USD", "UZS", usd_to_uzs),
        ("UZS", "USD", uzs_to_usd),
    ):
        result = await db.execute(
            select(ExchangeRate).where(
                ExchangeRate.from_currency == from_curr,
                ExchangeRate.to_currency == to_curr,
            )
        )
        existing = result.scalar_one_or_none()
        if not existing:
            db.add(
                ExchangeRate(
                    from_currency=from_curr,
                    to_currency=to_curr,
                    rate=rate,
                )
            )
    await db.flush()


async def get_exchange_rate(db: AsyncSession, from_currency: str, to_currency: str) -> Decimal:
    from_curr = normalize_currency(from_currency, "UZS")
    to_curr = normalize_currency(to_currency, "UZS")

    if from_curr == to_curr:
        return Decimal("1")

    cache = _fx_cache(db)
    cache_key = (from_curr, to_curr)
    cached_rate = cache.get(cache_key)
    if cached_rate is not None:
        return cached_rate

    result = await db.execute(
        select(ExchangeRate).where(
            ExchangeRate.from_currency == from_curr,
            ExchangeRate.to_currency == to_curr,
        )
    )
    rate = result.scalar_one_or_none()
    if rate:
        resolved_rate = _to_decimal(rate.rate)
        cache[cache_key] = resolved_rate
        return resolved_rate

    if {from_curr, to_curr} == {"USD", "UZS"}:
        await _ensure_default_usd_uzs_rates(db)
        result = await db.execute(
            select(ExchangeRate).where(
                ExchangeRate.from_currency == from_curr,
                ExchangeRate.to_currency == to_curr,
            )
        )
        rate = result.scalar_one_or_none()
        if rate:
            resolved_rate = _to_decimal(rate.rate)
            cache[cache_key] = resolved_rate
            return resolved_rate

    raise ValueError(f"Exchange rate not found for {from_curr}->{to_curr}")


async def convert_amount(
    db: AsyncSession,
    amount: Decimal | float | int | str,
    from_currency: str,
    to_currency: str,
) -> Decimal:
    from_curr = normalize_currency(from_currency, "UZS")
    to_curr = normalize_currency(to_currency, "UZS")
    value = _to_decimal(amount)
    if from_curr == to_curr:
        return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    rate = await get_exchange_rate(db, from_curr, to_curr)
    converted = value * rate
    return converted.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


async def _sum_converted(
    db: AsyncSession,
    rows: Iterable[tuple[Decimal, str]],
    target_currency: str,
) -> Decimal:
    total = Decimal("0")
    for amount, currency in rows:
        total += await convert_amount(db, amount, currency, target_currency)
    return total.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


async def get_resolved_group_id(
    db: AsyncSession,
    user: User,
    group_id: int | None = None,
) -> int:
    return int(group_id or await get_active_group_id(db, user))


def recalculate_debt_status(debt: Debt) -> str:
    if debt.archived_at:
        debt.status = "archived"
        return debt.status
    if Decimal(str(debt.remaining_amount)) <= Decimal("0"):
        debt.status = "fully_repaid"
        if not debt.paid_at:
            debt.paid_at = datetime.now(timezone.utc)
    elif Decimal(str(debt.remaining_amount)) < Decimal(str(debt.amount)):
        debt.status = "partially_repaid"
    else:
        debt.status = "active"
    return debt.status


async def get_user_main_balance_summary(
    db: AsyncSession,
    user: User,
    target_currency: str | None = None,
    group_id: int | None = None,
) -> dict[str, Decimal | str]:
    currency = normalize_currency(target_currency or user.default_currency, "UZS")
    resolved_group_id = await get_resolved_group_id(db, user, group_id)

    income_rows = (
        await db.execute(
            select(Transaction.amount, Transaction.currency).where(
                Transaction.user_id == user.id,
                Transaction.group_id == resolved_group_id,
                Transaction.type == TransactionType.INCOME,
            )
        )
    ).all()
    own_income = await _sum_converted(db, income_rows, currency)

    own_expense_rows = (
        await db.execute(
            select(Transaction.amount, Transaction.currency)
            .outerjoin(TransferExpense, TransferExpense.transaction_id == Transaction.id)
            .where(
                Transaction.user_id == user.id,
                Transaction.group_id == resolved_group_id,
                Transaction.type.in_(
                    [TransactionType.EXPENSE, TransactionType.TRANSFER_OUT, TransactionType.DEBT_PAYMENT]
                ),
                Transaction.funding_source == "main",
                TransferExpense.transaction_id.is_(None),
            )
        )
    ).all()
    own_expense = await _sum_converted(db, own_expense_rows, currency)

    transfer_rows = (
        await db.execute(
            select(Transfer.remaining_amount, Transfer.currency).where(
                Transfer.group_id == resolved_group_id,
                Transfer.recipient_id == user.id,
                Transfer.status == TransferStatus.COMPLETED,
                Transfer.remaining_amount > 0,
            )
        )
    ).all()
    received_balance = await _sum_converted(db, transfer_rows, currency)

    own_balance = (own_income - own_expense).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    total_balance = (own_balance + received_balance).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return {
        "currency": currency,
        "group_id": resolved_group_id,
        "total_balance": total_balance,
        "own_balance": own_balance,
        "received_balance": received_balance,
    }


async def get_user_debt_summary(
    db: AsyncSession,
    user: User,
    target_currency: str | None = None,
    group_id: int | None = None,
) -> dict[str, Decimal | str]:
    currency = normalize_currency(target_currency or user.default_currency, "UZS")
    resolved_group_id = await get_resolved_group_id(db, user, group_id)

    debts = (
        await db.execute(
            select(Debt).where(
                Debt.user_id == user.id,
                Debt.group_id == resolved_group_id,
                Debt.status != "archived",
            )
        )
    ).scalars().all()

    available_debt = Decimal("0")
    outstanding_debt = Decimal("0")
    for debt in debts:
        if debt.status in {"active", "partially_repaid"}:
            available_native = max(Decimal("0"), _to_decimal(debt.amount) - _to_decimal(debt.used_amount))
            available_debt += await convert_amount(db, available_native, debt.currency, currency)
        outstanding_debt += await convert_amount(db, debt.remaining_amount, debt.currency, currency)

    return {
        "currency": currency,
        "group_id": resolved_group_id,
        "available_debt_balance": available_debt.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
        "outstanding_debt_balance": outstanding_debt.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
    }


async def get_user_balance_summary(
    db: AsyncSession,
    user: User,
    target_currency: str | None = None,
    group_id: int | None = None,
) -> dict[str, Decimal | str]:
    main = await get_user_main_balance_summary(db, user, target_currency, group_id)
    debt = await get_user_debt_summary(db, user, main["currency"], group_id)
    return {
        **main,
        "debt_balance": debt["available_debt_balance"],
        "outstanding_debt_balance": debt["outstanding_debt_balance"],
    }


async def allocate_expense_to_transfers(
    db: AsyncSession,
    user_id: int,
    group_id: int,
    transaction_id,
    amount: Decimal | float | int | str,
    currency: str,
    category_id: int | None,
    description: str | None = None,
) -> None:
    remaining = _to_decimal(amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    expense_currency = normalize_currency(currency, "UZS")
    if remaining <= 0:
        return

    transfers_result = await db.execute(
        select(Transfer)
        .where(
            Transfer.group_id == group_id,
            Transfer.recipient_id == user_id,
            Transfer.status == TransferStatus.COMPLETED,
            Transfer.remaining_amount > 0,
        )
        .order_by(Transfer.created_at.asc())
    )
    transfers = transfers_result.scalars().all()

    for transfer in transfers:
        if remaining <= 0:
            break

        available_transfer_currency = _to_decimal(transfer.remaining_amount)
        available_expense_currency = await convert_amount(
            db,
            available_transfer_currency,
            transfer.currency,
            expense_currency,
        )
        if available_expense_currency <= 0:
            continue

        used_expense_currency = min(remaining, available_expense_currency)
        used_transfer_currency = await convert_amount(
            db,
            used_expense_currency,
            expense_currency,
            transfer.currency,
        )
        if used_transfer_currency > available_transfer_currency:
            used_transfer_currency = available_transfer_currency

        transfer.remaining_amount = (
            available_transfer_currency - used_transfer_currency
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

        db.add(
            TransferExpense(
                group_id=group_id,
                transfer_id=transfer.id,
                transaction_id=transaction_id,
                amount=used_transfer_currency,
                description=description,
                category_id=category_id,
            )
        )

        remaining = (remaining - used_expense_currency).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


async def get_spendable_main_balance(
    db: AsyncSession,
    user: User,
    currency: str | None = None,
    group_id: int | None = None,
) -> Decimal:
    summary = await get_user_main_balance_summary(db, user, currency, group_id)
    return _to_decimal(summary["total_balance"])


async def get_available_debt_for_entry(
    db: AsyncSession,
    debt: Debt,
    target_currency: str | None = None,
) -> Decimal:
    currency = normalize_currency(target_currency or debt.currency, "UZS")
    if debt.status not in {"active", "partially_repaid"}:
        return Decimal("0.00")
    available_native = max(Decimal("0"), _to_decimal(debt.amount) - _to_decimal(debt.used_amount))
    return await convert_amount(db, available_native, debt.currency, currency)


async def apply_debt_usage(
    db: AsyncSession,
    *,
    debt: Debt,
    transaction: Transaction,
    amount: Decimal,
    currency: str,
    note: str | None = None,
) -> DebtUsage:
    native_amount = await convert_amount(db, amount, currency, debt.currency)
    available_native = max(Decimal("0"), _to_decimal(debt.amount) - _to_decimal(debt.used_amount))
    if native_amount > available_native:
        raise ValueError("Selected debt source does not have enough available balance")

    debt.used_amount = (_to_decimal(debt.used_amount) + native_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    usage = DebtUsage(
        debt_id=debt.id,
        group_id=debt.group_id,
        transaction_id=transaction.id,
        amount=native_amount,
        currency=debt.currency,
        note=note,
    )
    db.add(usage)
    await db.flush()
    return usage


async def apply_debt_repayment(
    db: AsyncSession,
    *,
    debt: Debt,
    user: User,
    amount: Decimal,
    currency: str,
    note: str | None = None,
) -> DebtRepayment:
    payment_currency = normalize_currency(currency, user.default_currency)
    converted_amount = await convert_amount(db, amount, payment_currency, debt.currency)
    remaining_native = _to_decimal(debt.remaining_amount)
    if converted_amount > remaining_native:
        converted_amount = remaining_native

    debt.remaining_amount = (remaining_native - converted_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    recalculate_debt_status(debt)
    if debt.remaining_amount <= 0 and not debt.paid_at:
        debt.paid_at = datetime.now(timezone.utc)

    repayment = DebtRepayment(
        debt_id=debt.id,
        group_id=debt.group_id,
        user_id=user.id,
        amount=amount,
        currency=payment_currency,
        converted_amount=converted_amount,
        note=note,
    )
    db.add(repayment)
    await db.flush()
    return repayment
