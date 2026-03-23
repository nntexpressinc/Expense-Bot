from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.finance import MONEY_QUANT, convert_amount, normalize_currency
from database.models import AttendanceEntry, Worker, WorkerAdvance, WorkerPayment


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _period_days(start_date: date, end_date: date) -> int:
    return max(1, (end_date - start_date).days + 1)


def attendance_units(entry: AttendanceEntry) -> Decimal:
    status = (entry.status or "present").lower()
    units = _to_decimal(entry.units or 0)
    if status == "absent":
        return Decimal("0")
    if status == "half_day":
        return Decimal("0.5")
    if status == "custom":
        return units
    return units if units > 0 else Decimal("1")


async def calculate_worker_period_summary(
    db: AsyncSession,
    worker: Worker,
    start_date: date,
    end_date: date,
    target_currency: Optional[str] = None,
) -> dict:
    currency = normalize_currency(target_currency or worker.currency, "UZS")

    attendance_entries = (
        await db.execute(
            select(AttendanceEntry).where(
                AttendanceEntry.worker_id == worker.id,
                AttendanceEntry.entry_date >= start_date,
                AttendanceEntry.entry_date <= end_date,
            )
        )
    ).scalars().all()

    advances = (
        await db.execute(
            select(WorkerAdvance).where(
                WorkerAdvance.worker_id == worker.id,
                WorkerAdvance.payment_date >= start_date,
                WorkerAdvance.payment_date <= end_date,
            )
        )
    ).scalars().all()

    payments = (
        await db.execute(
            select(WorkerPayment).where(
                WorkerPayment.worker_id == worker.id,
                WorkerPayment.payment_date >= start_date,
                WorkerPayment.payment_date <= end_date,
            )
        )
    ).scalars().all()

    base_native = Decimal("0")
    quantity = Decimal("0")
    rate = _to_decimal(worker.rate)
    payment_type = (worker.payment_type or "daily").lower()

    if payment_type == "daily":
        quantity = sum(attendance_units(entry) for entry in attendance_entries)
        base_native = quantity * rate
    elif payment_type == "monthly":
        total_days = Decimal(str(_period_days(start_date, end_date)))
        active_from = max(start_date, worker.start_date)
        active_days = Decimal(str(_period_days(active_from, end_date))) if active_from <= end_date else Decimal("0")
        quantity = active_days
        base_native = (rate * active_days / total_days) if total_days > 0 else Decimal("0")
    else:
        quantity = sum(attendance_units(entry) for entry in attendance_entries)
        base_native = quantity * rate

    advance_native = sum(_to_decimal(item.amount) for item in advances)
    payment_native = sum(_to_decimal(item.amount) for item in payments)
    payable_native = max(Decimal("0"), base_native - advance_native - payment_native)

    base = await convert_amount(db, base_native, worker.currency, currency)
    advance_total = await convert_amount(db, advance_native, worker.currency, currency)
    payment_total = await convert_amount(db, payment_native, worker.currency, currency)
    payable = await convert_amount(db, payable_native, worker.currency, currency)

    if payable <= Decimal("0.00") and (advance_total > 0 or payment_total > 0 or base > 0):
        status = "paid"
    elif payment_total > 0 or advance_total > 0:
        status = "partial"
    else:
        status = "unpaid"

    return {
        "worker_id": str(worker.id),
        "group_id": worker.group_id,
        "full_name": worker.full_name,
        "role_name": worker.role_name,
        "payment_type": payment_type,
        "rate": float((await convert_amount(db, rate, worker.currency, currency)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)),
        "quantity": float(quantity.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)),
        "base_amount": float(base),
        "advance_amount": float(advance_total),
        "paid_amount": float(payment_total),
        "payable_amount": float(payable),
        "status": status,
        "currency": currency,
        "attendance_count": len(attendance_entries),
        "advances_count": len(advances),
        "payments_count": len(payments),
    }


async def calculate_group_payroll_summary(
    db: AsyncSession,
    group_id: int,
    start_date: date,
    end_date: date,
    target_currency: str = "UZS",
    include_inactive: bool = False,
) -> dict:
    query = select(Worker).where(Worker.group_id == group_id)
    if not include_inactive:
        query = query.where(Worker.is_active.is_(True))

    workers = (await db.execute(query.order_by(Worker.full_name.asc()))).scalars().all()
    summaries = []
    totals = {
        "base_amount": Decimal("0"),
        "advance_amount": Decimal("0"),
        "paid_amount": Decimal("0"),
        "payable_amount": Decimal("0"),
    }

    for worker in workers:
        summary = await calculate_worker_period_summary(db, worker, start_date, end_date, target_currency)
        summaries.append(summary)
        totals["base_amount"] += Decimal(str(summary["base_amount"]))
        totals["advance_amount"] += Decimal(str(summary["advance_amount"]))
        totals["paid_amount"] += Decimal(str(summary["paid_amount"]))
        totals["payable_amount"] += Decimal(str(summary["payable_amount"]))

    return {
        "group_id": group_id,
        "currency": target_currency,
        "workers": summaries,
        "totals": {key: float(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)) for key, value in totals.items()},
    }
