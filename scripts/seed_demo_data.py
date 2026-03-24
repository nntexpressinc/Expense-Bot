from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from database.finance import apply_debt_repayment, apply_debt_usage, get_user_balance_summary
from database.models import (
    AttendanceEntry,
    Debt,
    Group,
    Transaction,
    TransactionType,
    Transfer,
    TransferStatus,
    User,
    UserGroup,
    Worker,
    WorkerAdvance,
    WorkerPayment,
)
from database.session import async_session_factory
from database.workers import calculate_group_payroll_summary

DEMO_TAG = "[DEMO 2026-03-24]"
TARGET_GROUP = "Toshkent Office"
TARGET_USER_ID = 5780024333


def money(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def day_of_month(day: int) -> date:
    now = datetime.now(timezone.utc)
    return date(now.year, now.month, day)


def dt_of_month(day: int, hour: int = 10, minute: int = 0) -> datetime:
    return datetime.combine(day_of_month(day), datetime.min.time(), tzinfo=timezone.utc).replace(hour=hour, minute=minute)


def month_end() -> date:
    return (day_of_month(28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


async def create_transaction(
    db,
    *,
    user_id: int,
    group_id: int,
    tx_type: TransactionType,
    amount: Decimal,
    currency: str,
    description: str,
    when: datetime,
    funding_source: str = "main",
    debt_kind: str | None = None,
    transfer_id=None,
):
    tx = Transaction(
        user_id=user_id,
        group_id=group_id,
        type=tx_type,
        amount=amount,
        currency=currency,
        description=description,
        transaction_date=when,
        funding_source=funding_source,
        debt_kind=debt_kind,
        transfer_id=transfer_id,
    )
    db.add(tx)
    await db.flush()
    return tx


async def main():
    async with async_session_factory() as db:
        group = (
            await db.execute(select(Group).where(Group.name == TARGET_GROUP))
        ).scalar_one_or_none()
        if not group:
            raise SystemExit(f"Group not found: {TARGET_GROUP}")

        user = (
            await db.execute(select(User).where(User.id == TARGET_USER_ID))
        ).scalar_one_or_none()
        if not user:
            raise SystemExit(f"User not found: {TARGET_USER_ID}")

        membership = (
            await db.execute(
                select(UserGroup).where(UserGroup.group_id == group.id, UserGroup.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not membership:
            raise SystemExit(f"User {TARGET_USER_ID} is not in group {TARGET_GROUP}")

        marker_exists = (
            await db.execute(
                select(Transaction).where(
                    Transaction.user_id == user.id,
                    Transaction.group_id == group.id,
                    Transaction.description == f"{DEMO_TAG} Seed marker",
                )
            )
        ).scalar_one_or_none()
        if marker_exists:
            print(f"Seed already exists for {TARGET_GROUP} / {TARGET_USER_ID}.")
            before = await get_user_balance_summary(db, user, user.default_currency, group.id)
            payroll = await calculate_group_payroll_summary(
                db,
                group_id=group.id,
                start_date=day_of_month(1),
                end_date=month_end(),
                target_currency=user.default_currency,
            )
            print("Current balance summary:", before)
            print("Current payroll totals:", payroll["totals"])
            return

        other_user = (
            await db.execute(
                select(User)
                .join(UserGroup, UserGroup.user_id == User.id)
                .where(UserGroup.group_id == group.id, User.id != user.id)
                .order_by(User.id.asc())
            )
        ).scalar_one_or_none()
        if not other_user:
            raise SystemExit(f"No second user found in group {TARGET_GROUP}")

        before = await get_user_balance_summary(db, user, user.default_currency, group.id)

        # Marker
        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.INCOME,
            amount=money("0.01"),
            currency="USD",
            description=f"{DEMO_TAG} Seed marker",
            when=dt_of_month(1, 9, 0),
        )

        # Incomes
        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.INCOME,
            amount=money("1200"),
            currency="USD",
            description=f"{DEMO_TAG} Project income",
            when=dt_of_month(2, 10, 0),
        )
        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.INCOME,
            amount=money("2460000"),
            currency="UZS",
            description=f"{DEMO_TAG} Cash office income",
            when=dt_of_month(4, 11, 0),
        )

        # Main-balance expenses
        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.EXPENSE,
            amount=money("180"),
            currency="USD",
            description=f"{DEMO_TAG} Fuel and logistics",
            when=dt_of_month(6, 14, 0),
            funding_source="main",
        )
        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.EXPENSE,
            amount=money("615000"),
            currency="UZS",
            description=f"{DEMO_TAG} Materials purchase",
            when=dt_of_month(8, 13, 0),
            funding_source="main",
        )

        # Transfer in for extra received balance.
        transfer = Transfer(
            group_id=group.id,
            sender_id=other_user.id,
            recipient_id=user.id,
            amount=money("350"),
            currency="USD",
            description=f"{DEMO_TAG} Internal transfer for office",
            status=TransferStatus.COMPLETED,
            remaining_amount=money("350"),
            created_at=dt_of_month(9, 12, 30),
            completed_at=dt_of_month(9, 12, 35),
        )
        db.add(transfer)
        await db.flush()
        await create_transaction(
            db,
            user_id=other_user.id,
            group_id=group.id,
            tx_type=TransactionType.TRANSFER_OUT,
            amount=money("350"),
            currency="USD",
            description=f"{DEMO_TAG} Transfer to {user.first_name}",
            when=dt_of_month(9, 12, 35),
            transfer_id=transfer.id,
        )
        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.TRANSFER_IN,
            amount=money("350"),
            currency="USD",
            description=f"{DEMO_TAG} Transfer received from {other_user.first_name}",
            when=dt_of_month(9, 12, 35),
            transfer_id=transfer.id,
        )

        # Debts
        cash_loan_usd = Debt(
            user_id=user.id,
            group_id=group.id,
            amount=money("500"),
            remaining_amount=money("500"),
            used_amount=money("0"),
            kind="cash_loan",
            currency="USD",
            description=f"{DEMO_TAG} Borrowed for office reserve",
            source_name="DEMO: Hasan aka",
            source_contact="+998901112233",
            status="active",
            created_at=dt_of_month(10, 10, 0),
        )
        cash_loan_uzs = Debt(
            user_id=user.id,
            group_id=group.id,
            amount=money("1230000"),
            remaining_amount=money("1230000"),
            used_amount=money("0"),
            kind="cash_loan",
            currency="UZS",
            description=f"{DEMO_TAG} Borrowed in UZS",
            source_name="DEMO: Rustam aka",
            source_contact="+998907778899",
            status="active",
            created_at=dt_of_month(11, 10, 0),
        )
        credit_purchase = Debt(
            user_id=user.id,
            group_id=group.id,
            amount=money("300"),
            remaining_amount=money("300"),
            used_amount=money("0"),
            kind="credit_purchase",
            currency="USD",
            description=f"{DEMO_TAG} Bought on credit",
            source_name="DEMO: Texno market",
            source_contact="+998905556677",
            status="active",
            created_at=dt_of_month(12, 15, 0),
        )
        db.add_all([cash_loan_usd, cash_loan_uzs, credit_purchase])
        await db.flush()

        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.DEBT,
            amount=money("500"),
            currency="USD",
            description=f"{DEMO_TAG} Borrowed for office reserve",
            when=dt_of_month(10, 10, 5),
            debt_kind="cash_loan",
        )
        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.DEBT,
            amount=money("1230000"),
            currency="UZS",
            description=f"{DEMO_TAG} Borrowed in UZS",
            when=dt_of_month(11, 10, 5),
            debt_kind="cash_loan",
        )
        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.DEBT,
            amount=money("300"),
            currency="USD",
            description=f"{DEMO_TAG} Bought on credit",
            when=dt_of_month(12, 15, 5),
            debt_kind="credit_purchase",
        )

        debt_expense = await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.EXPENSE,
            amount=money("135"),
            currency="USD",
            description=f"{DEMO_TAG} Equipment from borrowed cash",
            when=dt_of_month(13, 11, 30),
            funding_source="debt",
        )
        await apply_debt_usage(
            db,
            debt=cash_loan_usd,
            transaction=debt_expense,
            amount=money("135"),
            currency="USD",
            note=f"{DEMO_TAG} Debt source usage",
        )

        await apply_debt_repayment(
            db,
            debt=cash_loan_usd,
            user=user,
            amount=money("50"),
            currency="USD",
            note=f"{DEMO_TAG} Partial repayment",
        )
        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.DEBT_PAYMENT,
            amount=money("50"),
            currency="USD",
            description=f"{DEMO_TAG} Debt repayment USD",
            when=dt_of_month(15, 12, 0),
            funding_source="main",
        )

        await apply_debt_repayment(
            db,
            debt=credit_purchase,
            user=user,
            amount=money("40"),
            currency="USD",
            note=f"{DEMO_TAG} Credit purchase repayment",
        )
        await create_transaction(
            db,
            user_id=user.id,
            group_id=group.id,
            tx_type=TransactionType.DEBT_PAYMENT,
            amount=money("40"),
            currency="USD",
            description=f"{DEMO_TAG} Debt repayment credit purchase",
            when=dt_of_month(18, 17, 0),
            funding_source="main",
        )

        # Workers
        worker_monthly = Worker(
            group_id=group.id,
            full_name="[DEMO] Anvar Karimov",
            role_name="IT - Oylik",
            payment_type="monthly",
            rate=money("600"),
            currency="USD",
            start_date=day_of_month(1),
            created_by=user.id,
            is_active=True,
        )
        worker_daily = Worker(
            group_id=group.id,
            full_name="[DEMO] Sardor Usta",
            role_name="Usta - Kunlik",
            payment_type="daily",
            rate=money("25"),
            currency="USD",
            start_date=day_of_month(1),
            created_by=user.id,
            is_active=True,
        )
        worker_volume = Worker(
            group_id=group.id,
            full_name="[DEMO] Dilshod Mebel",
            role_name="Mebel - Hajm",
            payment_type="volume",
            rate=money("12"),
            currency="USD",
            start_date=day_of_month(1),
            created_by=user.id,
            is_active=True,
        )
        db.add_all([worker_monthly, worker_daily, worker_volume])
        await db.flush()

        def add_attendance(worker_id, day: int, status: str, units: str = "0"):
            db.add(
                AttendanceEntry(
                    worker_id=worker_id,
                    group_id=group.id,
                    entry_date=day_of_month(day),
                    status=status,
                    units=money(units),
                    comment=DEMO_TAG,
                    created_by=user.id,
                )
            )

        for day in [1, 2, 3, 5, 6, 9, 10, 12, 16, 17, 19, 20]:
            add_attendance(worker_monthly.id, day, "present")
        for day in [7]:
            add_attendance(worker_monthly.id, day, "half_day")
        for day in [14, 21]:
            add_attendance(worker_monthly.id, day, "absent")

        for day in [1, 2, 4, 5, 6, 8, 9, 11, 12, 15, 16, 18, 19, 22]:
            add_attendance(worker_daily.id, day, "present")
        for day in [13, 20]:
            add_attendance(worker_daily.id, day, "half_day")
        for day in [3, 10, 17]:
            add_attendance(worker_daily.id, day, "absent")

        for day, units in [(2, "8"), (5, "10"), (9, "9"), (14, "7")]:
            add_attendance(worker_volume.id, day, "custom", units)

        db.add_all(
            [
                WorkerAdvance(
                    worker_id=worker_monthly.id,
                    group_id=group.id,
                    amount=money("50"),
                    currency="USD",
                    payment_date=day_of_month(21),
                    note=f"{DEMO_TAG} Monthly advance",
                    created_by=user.id,
                ),
                WorkerAdvance(
                    worker_id=worker_daily.id,
                    group_id=group.id,
                    amount=money("50"),
                    currency="USD",
                    payment_date=day_of_month(20),
                    note=f"{DEMO_TAG} Daily advance",
                    created_by=user.id,
                ),
                WorkerAdvance(
                    worker_id=worker_volume.id,
                    group_id=group.id,
                    amount=money("60"),
                    currency="USD",
                    payment_date=day_of_month(22),
                    note=f"{DEMO_TAG} Volume advance",
                    created_by=user.id,
                ),
                WorkerPayment(
                    worker_id=worker_daily.id,
                    group_id=group.id,
                    amount=money("100"),
                    currency="USD",
                    payment_date=day_of_month(23),
                    note=f"{DEMO_TAG} Daily partial payment",
                    created_by=user.id,
                ),
                WorkerPayment(
                    worker_id=worker_volume.id,
                    group_id=group.id,
                    amount=money("120"),
                    currency="USD",
                    payment_date=day_of_month(23),
                    note=f"{DEMO_TAG} Volume partial payment",
                    created_by=user.id,
                ),
            ]
        )

        for amount, day, label in [
            ("50", 21, "Monthly advance"),
            ("50", 20, "Daily advance"),
            ("60", 22, "Volume advance"),
            ("100", 23, "Daily payment"),
            ("120", 23, "Volume payment"),
        ]:
            await create_transaction(
                db,
                user_id=user.id,
                group_id=group.id,
                tx_type=TransactionType.EXPENSE,
                amount=money(amount),
                currency="USD",
                description=f"{DEMO_TAG} {label}",
                when=dt_of_month(day, 18, 0),
                funding_source="main",
            )

        await db.commit()

        after = await get_user_balance_summary(db, user, user.default_currency, group.id)
        payroll = await calculate_group_payroll_summary(
            db,
            group_id=group.id,
            start_date=day_of_month(1),
            end_date=month_end(),
            target_currency=user.default_currency,
        )

        print("Before balance summary:", before)
        print("After balance summary:", after)
        print("Expected demo deltas (USD target):")
        print("  main balance approx +1049.99 USD (includes 0.01 marker)")
        print("  debt balance approx +465.00 USD")
        print("  outstanding debt approx +810.00 USD")
        print("Payroll totals:", payroll["totals"])
        for worker in payroll["workers"]:
            if worker["full_name"].startswith("[DEMO]"):
                print(worker)


if __name__ == "__main__":
    asyncio.run(main())
