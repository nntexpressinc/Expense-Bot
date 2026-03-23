from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from aiogram import Bot
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.notifications import notify_admins_about_transaction, notify_transfer_participants
from config.admin import check_user_admin_status, is_user_admin
from config.constants import DEFAULT_EXCHANGE_RATE
from config.settings import settings
from database.audit import write_audit_log
from database.finance import (
    MONEY_QUANT,
    allocate_expense_to_transfers,
    apply_debt_repayment,
    apply_debt_usage,
    calculate_available_debt_source_native,
    convert_amount,
    get_available_debt_for_entry,
    get_resolved_group_id,
    get_spendable_main_balance,
    get_user_balance_summary,
    normalize_currency,
    normalize_debt_kind,
    normalize_funding_source,
)
from database.group_context import (
    add_user_to_group,
    ensure_user_setup,
    get_active_group,
    get_active_group_id,
    is_group_admin,
    list_user_groups,
    set_active_group,
)
from database.models import (
    Category,
    CategoryType,
    Debt,
    DebtRepayment,
    ExchangeRate,
    Group,
    Transaction,
    TransactionType,
    Transfer,
    TransferExpense,
    TransferStatus,
    User,
    UserGroup,
)
from database.session import async_session_factory


SYSTEM_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "income": [
        ("Salary", "??"),
        ("Sales", "??"),
        ("Transfer In", "??"),
        ("Other income", "?"),
    ],
    "expense": [
        ("Food", "??"),
        ("Transport", "??"),
        ("Materials", "??"),
        ("Debt repayment", "??"),
        ("Other expense", "?"),
    ],
}


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _money(value: Decimal | float | int | str) -> Decimal:
    return _to_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _lang(value: str | None) -> str:
    text = (value or "uz").split("-")[0].lower()
    if text in {"uz", "ru", "en"}:
        return text
    return "uz"


def _display_user(user: User | None) -> str:
    if not user:
        return "-"
    if user.username:
        return f"@{user.username}"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return full_name or str(user.id)


def _period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    period_key = (period or "month").lower()
    if period_key == "day":
        return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    if period_key == "week":
        day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        return day_start - timedelta(days=day_start.weekday())
    if period_key == "year":
        return datetime(now.year, 1, 1, tzinfo=timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


@asynccontextmanager
async def _session() -> AsyncSession:
    async with async_session_factory() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def _get_user_or_raise(db: AsyncSession, user_id: int) -> User:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise ValueError("User not found")
    await ensure_user_setup(db, user)
    return user


async def _ensure_system_categories(db: AsyncSession) -> None:
    for tx_type, items in SYSTEM_CATEGORIES.items():
        enum_type = CategoryType.INCOME if tx_type == "income" else CategoryType.EXPENSE
        for name, icon in items:
            exists = (
                await db.execute(
                    select(Category).where(
                        Category.name == name,
                        Category.type == enum_type,
                        Category.is_system.is_(True),
                        Category.user_id.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if not exists:
                db.add(Category(name=name, type=enum_type, icon=icon, is_system=True))
    await db.flush()


async def _ensure_exchange_rate_pair(
    db: AsyncSession,
    from_currency: str,
    to_currency: str,
) -> ExchangeRate:
    from_curr = normalize_currency(from_currency, "UZS")
    to_curr = normalize_currency(to_currency, "UZS")

    rate = (
        await db.execute(
            select(ExchangeRate).where(
                ExchangeRate.from_currency == from_curr,
                ExchangeRate.to_currency == to_curr,
            )
        )
    ).scalar_one_or_none()
    if rate:
        return rate

    if {from_curr, to_curr} == {"USD", "UZS"}:
        default_rate = Decimal(str(DEFAULT_EXCHANGE_RATE))
        calculated = default_rate if (from_curr, to_curr) == ("USD", "UZS") else (Decimal("1") / default_rate)
        rate = ExchangeRate(
            from_currency=from_curr,
            to_currency=to_curr,
            rate=calculated,
        )
        db.add(rate)
        await db.flush()
        return rate

    raise ValueError("Exchange rate not found")


async def _admin_check(db: AsyncSession, user: User, *, allow_group_admin: bool = False) -> None:
    if await check_user_admin_status(user):
        return
    if allow_group_admin and await is_group_admin(db, user):
        return
    raise PermissionError("Admin access required")


async def _notify_admins_if_needed(
    *,
    actor: User,
    transaction: Transaction,
    operation_key: str,
    category_name: str | None,
    bot: Bot | None,
) -> None:
    if not settings.ENABLE_NOTIFICATIONS:
        return

    owned_bot = False
    local_bot = bot
    if local_bot is None:
        local_bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        owned_bot = True

    try:
        await notify_admins_about_transaction(local_bot, actor, transaction, operation_key, category_name)
    finally:
        if owned_bot:
            await local_bot.session.close()


async def get_or_create_user(
    *,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    language_code: str | None = None,
) -> User:
    async with _session() as db:
        user = (await db.execute(select(User).where(User.id == telegram_id))).scalar_one_or_none()
        if not user:
            user = User(
                id=telegram_id,
                username=username,
                first_name=first_name or "User",
                last_name=last_name,
                language_code=_lang(language_code),
                default_currency="UZS",
                theme_preference="light",
                is_admin=is_user_admin(telegram_id),
            )
            db.add(user)
            await db.flush()
        else:
            user.username = username
            if first_name:
                user.first_name = first_name
            user.last_name = last_name
            if is_user_admin(user.id):
                user.is_admin = True
            if not user.language_code:
                user.language_code = _lang(language_code)
            if not user.default_currency:
                user.default_currency = "UZS"
            if not getattr(user, "theme_preference", None):
                user.theme_preference = "light"

        await ensure_user_setup(db, user)
        await db.refresh(user)
        return user


async def get_user(telegram_id: int) -> User | None:
    async with _session() as db:
        user = (await db.execute(select(User).where(User.id == telegram_id))).scalar_one_or_none()
        if user:
            await ensure_user_setup(db, user)
        return user


async def set_user_language(user_id: int, language: str) -> User:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        user.language_code = _lang(language)
        await db.flush()
        await db.refresh(user)
        return user


async def set_user_currency(user_id: int, currency: str) -> User:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        user.default_currency = normalize_currency(currency, "UZS")
        await db.flush()
        await db.refresh(user)
        return user


async def set_user_theme(user_id: int, theme: str) -> User:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        user.theme_preference = "dark" if (theme or "").lower() == "dark" else "light"
        await db.flush()
        await db.refresh(user)
        return user


async def get_user_groups(user_id: int) -> list[dict[str, Any]]:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        return await list_user_groups(db, user.id)


async def set_user_active_group(user_id: int, group_id: int) -> Group:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        group = await set_active_group(db, user, group_id)
        await db.refresh(user)
        return group


async def join_user_group(inviter_id: int, invited_user_id: int) -> Group:
    async with _session() as db:
        inviter = await _get_user_or_raise(db, inviter_id)
        invited = await _get_user_or_raise(db, invited_user_id)
        active_group = await get_active_group(db, inviter)
        if not await is_group_admin(db, inviter, active_group.id) and not await check_user_admin_status(inviter):
            raise PermissionError("Group admin access required")
        await add_user_to_group(db, invited, active_group.id, "member")
        return active_group


async def is_admin(user_id: int) -> bool:
    async with _session() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            return is_user_admin(user_id)
        return await check_user_admin_status(user)


async def read_exchange_rate(from_currency: str, to_currency: str) -> Decimal:
    async with _session() as db:
        pair = await _ensure_exchange_rate_pair(db, from_currency, to_currency)
        return _money(pair.rate)


async def update_exchange_rate(
    actor_user_id: int,
    from_currency: str,
    to_currency: str,
    new_rate: Decimal,
) -> ExchangeRate:
    async with _session() as db:
        actor = await _get_user_or_raise(db, actor_user_id)
        await _admin_check(db, actor)

        from_curr = normalize_currency(from_currency, "UZS")
        to_curr = normalize_currency(to_currency, "UZS")
        rate_value = _to_decimal(new_rate)
        if rate_value <= 0:
            raise ValueError("Rate must be positive")

        record = await _ensure_exchange_rate_pair(db, from_curr, to_curr)
        record.rate = rate_value
        record.updated_by = actor.id

        if {from_curr, to_curr} == {"USD", "UZS"}:
            reverse = await _ensure_exchange_rate_pair(db, to_curr, from_curr)
            reverse.rate = (Decimal("1") / rate_value)
            reverse.updated_by = actor.id

        await write_audit_log(
            db,
            action="exchange_rate.updated",
            entity_type="exchange_rate",
            entity_id=f"{from_curr}-{to_curr}",
            actor=actor,
            group_id=await get_active_group_id(db, actor),
            payload={"rate": str(rate_value)},
        )
        await db.flush()
        await db.refresh(record)
        return record

async def get_categories(tx_type: str, user_id: int | None = None) -> list[dict[str, Any]]:
    async with _session() as db:
        await _ensure_system_categories(db)

        enum_type = CategoryType.INCOME if tx_type == "income" else CategoryType.EXPENSE
        query = select(Category).where(Category.type == enum_type)
        if user_id:
            query = query.where(or_(Category.is_system.is_(True), Category.user_id == user_id))
        else:
            query = query.where(Category.is_system.is_(True))

        categories = (
            await db.execute(
                query.order_by(Category.is_system.desc(), Category.name.asc(), Category.id.asc())
            )
        ).scalars().all()

        return [
            {
                "id": category.id,
                "name": category.name,
                "icon": category.icon or "",
                "is_system": category.is_system,
            }
            for category in categories
        ]


async def create_transaction(
    *,
    user_id: int,
    tx_type: str,
    amount: Decimal,
    category_id: int | None = None,
    description: str | None = None,
    currency: str | None = None,
    funding_source: str | None = None,
    debt_id: str | UUID | None = None,
    attachment_file_id: str | None = None,
    attachment_type: str | None = None,
    attachment_name: str | None = None,
    bot: Bot | None = None,
) -> Transaction:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        await _ensure_system_categories(db)

        current_group = await get_active_group_id(db, user)
        normalized_currency = normalize_currency(currency, user.default_currency)
        normalized_amount = _money(amount)
        if normalized_amount <= 0:
            raise ValueError("Amount must be positive")

        enum_map = {
            "income": TransactionType.INCOME,
            "expense": TransactionType.EXPENSE,
            "transfer_out": TransactionType.TRANSFER_OUT,
            "transfer_in": TransactionType.TRANSFER_IN,
            "debt": TransactionType.DEBT,
            "debt_payment": TransactionType.DEBT_PAYMENT,
        }
        transaction_type = enum_map.get((tx_type or "").lower())
        if not transaction_type:
            raise ValueError("Unsupported transaction type")

        category = None
        if category_id:
            category = (
                await db.execute(
                    select(Category).where(
                        Category.id == category_id,
                        or_(Category.is_system.is_(True), Category.user_id == user.id),
                    )
                )
            ).scalar_one_or_none()
            if not category:
                raise ValueError("Category not found")

        source = normalize_funding_source(funding_source)
        debt = None
        main_component = Decimal("0.00")
        debt_component = Decimal("0.00")
        if transaction_type == TransactionType.EXPENSE:
            if source == "main":
                spendable = await get_spendable_main_balance(db, user, normalized_currency, current_group)
                if normalized_amount > spendable:
                    raise ValueError(f"Insufficient main balance: {spendable:.2f} {normalized_currency}")
                main_component = normalized_amount
            else:
                if not debt_id:
                    raise ValueError("Debt source is required")
                debt_uuid = UUID(str(debt_id))
                debt = (
                    await db.execute(
                        select(Debt).where(
                            Debt.id == debt_uuid,
                            Debt.user_id == user.id,
                            Debt.group_id == current_group,
                        )
                    )
                ).scalar_one_or_none()
                if not debt:
                    raise ValueError("Debt entry not found")
                if normalize_debt_kind(getattr(debt, "kind", None)) != "cash_loan":
                    raise ValueError("Only borrowed money can be used as an expense source")
                spendable = await get_spendable_main_balance(db, user, normalized_currency, current_group)
                main_component = min(normalized_amount, spendable)
                debt_component = (normalized_amount - main_component).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
                if debt_component <= 0:
                    source = "main"
                    debt = None
                else:
                    available = await get_available_debt_for_entry(db, debt, normalized_currency)
                    if debt_component > available:
                        raise ValueError(
                            f"Insufficient debt balance: {available:.2f} {normalized_currency}. Create a new debt first."
                        )

        tx = Transaction(
            user_id=user.id,
            group_id=current_group,
            type=transaction_type,
            amount=normalized_amount,
            currency=normalized_currency,
            category_id=category.id if category else None,
            description=(description or None),
            funding_source=source,
            attachment_file_id=attachment_file_id,
            attachment_type=attachment_type,
            attachment_name=attachment_name,
            transaction_date=datetime.now(timezone.utc),
        )
        db.add(tx)
        await db.flush()

        if transaction_type == TransactionType.EXPENSE:
            if main_component > 0:
                await allocate_expense_to_transfers(
                    db,
                    user_id=user.id,
                    group_id=current_group,
                    transaction_id=tx.id,
                    amount=main_component,
                    currency=normalized_currency,
                    category_id=category.id if category else None,
                    description=description,
                )
            if debt and debt_component > 0:
                await apply_debt_usage(
                    db,
                    debt=debt,
                    transaction=tx,
                    amount=debt_component,
                    currency=normalized_currency,
                    note=description,
                )

        await write_audit_log(
            db,
            action=f"transaction.{transaction_type.value}.created",
            entity_type="transaction",
            entity_id=str(tx.id),
            actor=user,
            group_id=current_group,
            payload={
                "amount": str(normalized_amount),
                "currency": normalized_currency,
                "funding_source": source,
                "main_used_amount": str(main_component),
                "debt_used_amount": str(debt_component),
                "category_id": category.id if category else None,
            },
        )
        await db.flush()
        await db.refresh(tx)

        if transaction_type in {TransactionType.INCOME, TransactionType.EXPENSE}:
            await _notify_admins_if_needed(
                actor=user,
                transaction=tx,
                operation_key=transaction_type.value,
                category_name=category.name if category else None,
                bot=bot,
            )

        return tx


async def get_user_balance(user_id: int, currency: str | None = None) -> dict[str, Decimal | str | int]:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        summary = await get_user_balance_summary(db, user, currency)
        group = await get_active_group(db, user)
        return {
            "currency": summary["currency"],
            "group_id": summary["group_id"],
            "group_name": group.name,
            "total_balance": _money(summary["total_balance"]),
            "own_balance": _money(summary["own_balance"]),
            "received_balance": _money(summary["received_balance"]),
            "debt_balance": _money(summary["debt_balance"]),
            "outstanding_debt_balance": _money(summary["outstanding_debt_balance"]),
        }


async def get_user_statistics(
    user_id: int,
    *,
    period: str = "month",
    currency: str | None = None,
) -> dict[str, Any]:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        current_group = await get_active_group_id(db, user)
        display_currency = normalize_currency(currency, user.default_currency)
        since = _period_start(period)

        transactions = (
            await db.execute(
                select(Transaction)
                .where(
                    Transaction.user_id == user.id,
                    Transaction.group_id == current_group,
                    Transaction.transaction_date >= since,
                )
                .order_by(desc(Transaction.transaction_date))
            )
        ).scalars().all()

        total_income = Decimal("0")
        total_expense = Decimal("0")
        category_sums: dict[int | None, Decimal] = {}
        category_info: dict[int, tuple[str, str]] = {}
        category_ids = [tx.category_id for tx in transactions if tx.category_id]
        if category_ids:
            categories = (
                await db.execute(select(Category).where(Category.id.in_(sorted(set(category_ids)))))
            ).scalars().all()
            category_info = {cat.id: (cat.name, cat.icon or "??") for cat in categories}

        for tx in transactions:
            converted = await convert_amount(db, tx.amount, tx.currency, display_currency)
            if tx.type == TransactionType.INCOME:
                total_income += converted
            elif tx.type == TransactionType.EXPENSE or (
                tx.type == TransactionType.DEBT and normalize_debt_kind(getattr(tx, "debt_kind", None)) == "credit_purchase"
            ):
                total_expense += converted
                if tx.type == TransactionType.EXPENSE:
                    category_sums[tx.category_id] = category_sums.get(tx.category_id, Decimal("0")) + converted

        sent_transfers = (
            await db.execute(
                select(Transfer)
                .where(
                    Transfer.group_id == current_group,
                    Transfer.sender_id == user.id,
                    Transfer.created_at >= since,
                )
                .order_by(desc(Transfer.created_at))
            )
        ).scalars().all()
        received_transfers = (
            await db.execute(
                select(Transfer)
                .where(
                    Transfer.group_id == current_group,
                    Transfer.recipient_id == user.id,
                    Transfer.created_at >= since,
                )
                .order_by(desc(Transfer.created_at))
            )
        ).scalars().all()

        sent_total = Decimal("0")
        for transfer in sent_transfers:
            sent_total += await convert_amount(db, transfer.amount, transfer.currency, display_currency)
        received_total = Decimal("0")
        for transfer in received_transfers:
            received_total += await convert_amount(db, transfer.amount, transfer.currency, display_currency)

        top_categories: list[dict[str, Any]] = []
        for category_id, cat_total in sorted(category_sums.items(), key=lambda item: item[1], reverse=True)[:5]:
            name, icon = category_info.get(category_id or -1, ("Unknown", "??"))
            percent = float((cat_total / total_expense * Decimal("100")) if total_expense > 0 else Decimal("0"))
            top_categories.append(
                {
                    "id": category_id,
                    "name": name,
                    "icon": icon,
                    "amount": _money(cat_total),
                    "percent": percent,
                }
            )

        return {
            "period": period,
            "currency": display_currency,
            "total_income": _money(total_income),
            "total_expense": _money(total_expense),
            "difference": _money(total_income - total_expense),
            "top_categories": top_categories,
            "transfers_sent": _money(sent_total),
            "transfers_sent_count": len(sent_transfers),
            "transfers_received": _money(received_total),
            "transfers_received_count": len(received_transfers),
        }

async def resolve_recipient(
    *,
    requester_id: int,
    text: str | None = None,
    forwarded_user_id: int | None = None,
    forwarded_username: str | None = None,
    forwarded_first_name: str | None = None,
    forwarded_last_name: str | None = None,
) -> User | None:
    async with _session() as db:
        requester = await _get_user_or_raise(db, requester_id)
        current_group = await get_active_group_id(db, requester)

        async def _find_existing_by_id(user_id: int) -> User | None:
            return (
                await db.execute(
                    select(User)
                    .join(UserGroup, UserGroup.user_id == User.id)
                    .where(
                        User.id == user_id,
                        UserGroup.group_id == current_group,
                        User.is_active.is_(True),
                    )
                )
            ).scalar_one_or_none()

        if forwarded_user_id:
            existing = await _find_existing_by_id(forwarded_user_id)
            if existing:
                return existing

            created = User(
                id=forwarded_user_id,
                username=forwarded_username,
                first_name=forwarded_first_name or "User",
                last_name=forwarded_last_name,
                language_code=requester.language_code,
                default_currency="UZS",
                theme_preference="light",
            )
            db.add(created)
            await db.flush()
            await ensure_user_setup(db, created)
            await add_user_to_group(db, created, current_group, "member")
            await db.refresh(created)
            return created

        value = (text or "").strip()
        if not value:
            return None

        if value.startswith("@"):
            value = value[1:]

        query = select(User).join(UserGroup, UserGroup.user_id == User.id).where(
            UserGroup.group_id == current_group,
            User.is_active.is_(True),
        )
        if value.isdigit():
            query = query.where(User.id == int(value))
        else:
            query = query.where(func.lower(User.username) == value.lower())

        return (await db.execute(query)).scalar_one_or_none()


async def list_transfer_recipients(
    user_id: int,
    *,
    search: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        current_group = await get_active_group_id(db, user)
        query = (
            select(User)
            .join(UserGroup, UserGroup.user_id == User.id)
            .where(
                UserGroup.group_id == current_group,
                User.id != user.id,
                User.is_active.is_(True),
            )
        )
        if search:
            pattern = f"%{search.strip()}%"
            if search.strip():
                conditions = [
                    User.username.ilike(pattern),
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                ]
                if search.strip().isdigit():
                    conditions.append(User.id == int(search.strip()))
                query = query.where(or_(*conditions))

        users = (
            await db.execute(query.order_by(User.first_name.asc(), User.id.asc()).limit(limit))
        ).scalars().all()
        return [
            {
                "id": target.id,
                "username": target.username,
                "first_name": target.first_name,
                "last_name": target.last_name,
                "display_name": _display_user(target),
            }
            for target in users
        ]


async def create_transfer(
    *,
    sender_id: int,
    recipient_id: int,
    amount: Decimal,
    description: str | None = None,
    currency: str | None = None,
    bot: Bot | None = None,
) -> Transfer:
    async with _session() as db:
        sender = await _get_user_or_raise(db, sender_id)
        recipient = await _get_user_or_raise(db, recipient_id)
        current_group = await get_active_group_id(db, sender)

        sender_membership = (
            await db.execute(
                select(UserGroup).where(UserGroup.user_id == sender.id, UserGroup.group_id == current_group)
            )
        ).scalar_one_or_none()
        recipient_membership = (
            await db.execute(
                select(UserGroup).where(UserGroup.user_id == recipient.id, UserGroup.group_id == current_group)
            )
        ).scalar_one_or_none()
        if not sender_membership or not recipient_membership:
            raise ValueError("Recipient is not in the active group")
        if sender.id == recipient.id:
            raise ValueError("Cannot transfer to yourself")

        transfer_currency = normalize_currency(currency, sender.default_currency)
        transfer_amount = _money(amount)
        if transfer_amount <= 0:
            raise ValueError("Amount must be positive")

        sender_balance = await get_user_balance_summary(db, sender, transfer_currency, current_group)
        if transfer_amount > _to_decimal(sender_balance["own_balance"]):
            raise ValueError(f"Insufficient own balance: {_money(sender_balance['own_balance']):.2f} {transfer_currency}")

        transfer = Transfer(
            group_id=current_group,
            sender_id=sender.id,
            recipient_id=recipient.id,
            amount=transfer_amount,
            remaining_amount=transfer_amount,
            currency=transfer_currency,
            description=description,
            status=TransferStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(transfer)
        await db.flush()

        db.add(
            Transaction(
                user_id=sender.id,
                group_id=current_group,
                type=TransactionType.TRANSFER_OUT,
                amount=transfer_amount,
                currency=transfer_currency,
                description=description or f"Transfer to {_display_user(recipient)}",
                funding_source="main",
                transfer_id=transfer.id,
                transaction_date=datetime.now(timezone.utc),
            )
        )
        db.add(
            Transaction(
                user_id=recipient.id,
                group_id=current_group,
                type=TransactionType.TRANSFER_IN,
                amount=transfer_amount,
                currency=transfer_currency,
                description=description or f"Transfer from {_display_user(sender)}",
                funding_source="main",
                transfer_id=transfer.id,
                transaction_date=datetime.now(timezone.utc),
            )
        )

        await write_audit_log(
            db,
            action="transfer.created",
            entity_type="transfer",
            entity_id=str(transfer.id),
            actor=sender,
            group_id=current_group,
            payload={"recipient_id": recipient.id, "amount": str(transfer_amount), "currency": transfer_currency},
        )
        await db.flush()
        await db.refresh(transfer)

        await notify_transfer_participants(sender=sender, recipient=recipient, transfer=transfer, bot=bot)
        return transfer


async def list_sent_transfers(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        current_group = await get_active_group_id(db, user)
        transfers = (
            await db.execute(
                select(Transfer)
                .where(Transfer.sender_id == user.id, Transfer.group_id == current_group)
                .order_by(desc(Transfer.created_at))
                .limit(limit)
            )
        ).scalars().all()

        payload: list[dict[str, Any]] = []
        for transfer in transfers:
            recipient = (await db.execute(select(User).where(User.id == transfer.recipient_id))).scalar_one_or_none()
            payload.append(
                {
                    "id": str(transfer.id),
                    "name": _display_user(recipient),
                    "amount": _money(await convert_amount(db, transfer.amount, transfer.currency, user.default_currency)),
                    "remaining": _money(await convert_amount(db, transfer.remaining_amount, transfer.currency, user.default_currency)),
                    "currency": user.default_currency,
                    "created_at": transfer.created_at,
                }
            )
        return payload


async def list_received_transfers(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        current_group = await get_active_group_id(db, user)
        transfers = (
            await db.execute(
                select(Transfer)
                .where(Transfer.recipient_id == user.id, Transfer.group_id == current_group)
                .order_by(desc(Transfer.created_at))
                .limit(limit)
            )
        ).scalars().all()

        payload: list[dict[str, Any]] = []
        for transfer in transfers:
            sender = (await db.execute(select(User).where(User.id == transfer.sender_id))).scalar_one_or_none()
            payload.append(
                {
                    "id": str(transfer.id),
                    "name": _display_user(sender),
                    "amount": _money(await convert_amount(db, transfer.amount, transfer.currency, user.default_currency)),
                    "remaining": _money(await convert_amount(db, transfer.remaining_amount, transfer.currency, user.default_currency)),
                    "currency": user.default_currency,
                    "created_at": transfer.created_at,
                }
            )
        return payload


async def get_transfer_details(transfer_id: str | UUID, viewer_user_id: int) -> dict[str, Any] | None:
    async with _session() as db:
        user = await _get_user_or_raise(db, viewer_user_id)
        current_group = await get_active_group_id(db, user)
        transfer = (
            await db.execute(
                select(Transfer).where(
                    Transfer.id == UUID(str(transfer_id)),
                    Transfer.group_id == current_group,
                    or_(Transfer.sender_id == user.id, Transfer.recipient_id == user.id),
                )
            )
        ).scalar_one_or_none()
        if not transfer:
            return None

        counterpart_id = transfer.recipient_id if transfer.sender_id == user.id else transfer.sender_id
        counterpart = (await db.execute(select(User).where(User.id == counterpart_id))).scalar_one_or_none()

        expense_links = (
            await db.execute(
                select(TransferExpense, Transaction, Category)
                .outerjoin(Transaction, Transaction.id == TransferExpense.transaction_id)
                .outerjoin(Category, Category.id == TransferExpense.category_id)
                .where(TransferExpense.transfer_id == transfer.id)
                .order_by(desc(TransferExpense.created_at))
            )
        ).all()

        expenses: list[dict[str, Any]] = []
        spent_total = Decimal("0")
        for expense, transaction, category in expense_links:
            spent_amount = await convert_amount(db, expense.amount, transfer.currency, user.default_currency)
            spent_total += spent_amount
            expenses.append(
                {
                    "id": str(expense.id),
                    "amount": _money(spent_amount),
                    "currency": user.default_currency,
                    "category": category.name if category else "Unknown",
                    "description": expense.description or (transaction.description if transaction else None) or "-",
                    "date": (expense.created_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M"),
                }
            )

        converted_amount = await convert_amount(db, transfer.amount, transfer.currency, user.default_currency)
        converted_remaining = await convert_amount(db, transfer.remaining_amount, transfer.currency, user.default_currency)
        return {
            "id": str(transfer.id),
            "recipient": _display_user(counterpart),
            "amount": _money(converted_amount),
            "spent": _money(spent_total),
            "remaining": _money(converted_remaining),
            "currency": user.default_currency,
            "description": transfer.description or "-",
            "created_at": (transfer.created_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M"),
            "expenses": expenses,
        }

async def list_users_for_admin(
    admin_user_id: int,
    *,
    search: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    async with _session() as db:
        actor = await _get_user_or_raise(db, admin_user_id)
        global_admin = await check_user_admin_status(actor)
        active_group = await get_active_group_id(db, actor)

        if not global_admin and not await is_group_admin(db, actor, active_group):
            raise PermissionError("Admin access required")

        query = select(User).where(User.is_active.is_(True))
        if not global_admin:
            query = query.join(UserGroup, UserGroup.user_id == User.id).where(UserGroup.group_id == active_group)

        if search:
            search_term = search.strip()
            if search_term:
                pattern = f"%{search_term}%"
                conditions = [
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.username.ilike(pattern),
                ]
                if search_term.isdigit():
                    conditions.append(User.id == int(search_term))
                query = query.where(or_(*conditions))

        users = (
            await db.execute(query.order_by(User.first_name.asc(), User.id.asc()).limit(limit))
        ).scalars().all()

        payload = []
        for target in users:
            target_group = (
                await db.execute(select(Group).where(Group.id == target.active_group_id))
            ).scalar_one_or_none()
            payload.append(
                {
                    "id": target.id,
                    "username": target.username,
                    "first_name": target.first_name,
                    "last_name": target.last_name,
                    "language_code": target.language_code,
                    "default_currency": target.default_currency,
                    "is_active": target.is_active,
                    "is_admin": await check_user_admin_status(target),
                    "active_group_id": target.active_group_id,
                    "active_group_name": target_group.name if target_group else None,
                }
            )
        return payload


async def set_user_admin_role(admin_user_id: int, target_user_id: int, new_state: bool) -> None:
    async with _session() as db:
        actor = await _get_user_or_raise(db, admin_user_id)
        await _admin_check(db, actor)
        target = await _get_user_or_raise(db, target_user_id)
        if actor.id == target.id and not new_state:
            raise ValueError("Cannot remove your own admin role")
        target.is_admin = bool(new_state)
        await write_audit_log(
            db,
            action="user.admin_role.updated",
            entity_type="user",
            entity_id=str(target.id),
            actor=actor,
            group_id=await get_active_group_id(db, actor),
            payload={"is_admin": bool(new_state)},
        )
        await db.flush()


async def get_user_admin_snapshot(
    admin_user_id: int,
    target_user_id: int,
    *,
    currency: str | None = None,
) -> dict[str, Any]:
    async with _session() as db:
        actor = await _get_user_or_raise(db, admin_user_id)
        target = await _get_user_or_raise(db, target_user_id)

        global_admin = await check_user_admin_status(actor)
        if not global_admin and not await is_group_admin(db, actor):
            raise PermissionError("Admin access required")

        if not global_admin:
            actor_group = await get_active_group_id(db, actor)
            member = (
                await db.execute(
                    select(UserGroup).where(UserGroup.user_id == target.id, UserGroup.group_id == actor_group)
                )
            ).scalar_one_or_none()
            if not member:
                raise ValueError("User not found")

        display_currency = normalize_currency(currency, target.default_currency)
        target_group_id = await get_resolved_group_id(db, target, target.active_group_id)
        summary = await get_user_balance_summary(db, target, display_currency, target_group_id)
        group = (await db.execute(select(Group).where(Group.id == target_group_id))).scalar_one_or_none()

        debts = (
            await db.execute(
                select(Debt)
                .where(Debt.user_id == target.id, Debt.group_id == target_group_id)
                .order_by(desc(Debt.created_at))
                .limit(10)
            )
        ).scalars().all()
        repayments = (
            await db.execute(
                select(DebtRepayment)
                .join(Debt, Debt.id == DebtRepayment.debt_id)
                .where(DebtRepayment.user_id == target.id, Debt.group_id == target_group_id)
                .order_by(desc(DebtRepayment.repaid_at))
                .limit(10)
            )
        ).scalars().all()

        return {
            "id": target.id,
            "username": target.username,
            "first_name": target.first_name,
            "last_name": target.last_name,
            "language_code": target.language_code,
            "default_currency": target.default_currency,
            "is_active": target.is_active,
            "is_admin": await check_user_admin_status(target),
            "group_id": target_group_id,
            "group_name": group.name if group else None,
            "currency": display_currency,
            "total_balance": _money(summary["total_balance"]),
            "own_balance": _money(summary["own_balance"]),
            "received_balance": _money(summary["received_balance"]),
            "debt_balance": _money(summary["debt_balance"]),
            "outstanding_debt_balance": _money(summary["outstanding_debt_balance"]),
            "debt_entries_count": len(debts),
            "debt_repayments_count": len(repayments),
        }


async def delete_user_for_admin(admin_user_id: int, target_user_id: int) -> None:
    async with _session() as db:
        actor = await _get_user_or_raise(db, admin_user_id)
        await _admin_check(db, actor)
        if admin_user_id == target_user_id:
            raise ValueError("Cannot delete yourself")
        target = await _get_user_or_raise(db, target_user_id)
        await write_audit_log(
            db,
            action="user.deleted",
            entity_type="user",
            entity_id=str(target.id),
            actor=actor,
            group_id=await get_active_group_id(db, actor),
            payload={"username": target.username, "first_name": target.first_name},
        )
        await db.delete(target)


async def set_user_total_balance_for_admin(
    *,
    admin_user_id: int,
    target_user_id: int,
    target_total: Decimal,
    currency: str,
) -> None:
    async with _session() as db:
        actor = await _get_user_or_raise(db, admin_user_id)
        await _admin_check(db, actor)
        target = await _get_user_or_raise(db, target_user_id)

        target_currency = normalize_currency(currency, target.default_currency)
        target_group = await get_resolved_group_id(db, target, target.active_group_id)
        summary = await get_user_balance_summary(db, target, target_currency, target_group)
        current_total = _money(summary["total_balance"])
        desired_total = _money(target_total)
        delta = _money(desired_total - current_total)
        if delta == 0:
            return

        tx_type = TransactionType.INCOME if delta > 0 else TransactionType.EXPENSE
        amount = abs(delta)
        tx = Transaction(
            user_id=target.id,
            group_id=target_group,
            type=tx_type,
            amount=amount,
            currency=target_currency,
            description=f"Admin balance adjustment by {actor.id}",
            funding_source="main",
            transaction_date=datetime.now(timezone.utc),
        )
        db.add(tx)
        await write_audit_log(
            db,
            action="user.balance.adjusted",
            entity_type="user",
            entity_id=str(target.id),
            actor=actor,
            group_id=target_group,
            payload={"target_total": str(desired_total), "currency": target_currency, "delta": str(delta)},
        )
        await db.flush()

async def create_debt(
    user_id: int,
    amount: Decimal,
    currency: str | None,
    description: str | None = None,
    kind: str | None = None,
    *,
    source_name: str | None = None,
    source_contact: str | None = None,
    reference: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        current_group = await get_active_group_id(db, user)
        debt_amount = _money(amount)
        debt_currency = normalize_currency(currency, user.default_currency)
        debt_kind = normalize_debt_kind(kind)
        if debt_amount <= 0:
            raise ValueError("Amount must be positive")

        debt = Debt(
            user_id=user.id,
            group_id=current_group,
            amount=debt_amount,
            remaining_amount=debt_amount,
            used_amount=Decimal("0"),
            kind=debt_kind,
            currency=debt_currency,
            description=description,
            source_name=source_name,
            source_contact=source_contact,
            reference=reference,
            note=note,
            status="active",
        )
        db.add(debt)
        db.add(
            Transaction(
                user_id=user.id,
                group_id=current_group,
                type=TransactionType.DEBT,
                amount=debt_amount,
                currency=debt_currency,
                description=description or source_name or ("Borrowed money" if debt_kind == "cash_loan" else "Buy on credit"),
                funding_source="main",
                debt_kind=debt_kind,
                transaction_date=datetime.now(timezone.utc),
            )
        )
        await db.flush()
        await write_audit_log(
            db,
            action="debt.created",
            entity_type="debt",
            entity_id=str(debt.id),
            actor=user,
            group_id=current_group,
            payload={"amount": str(debt_amount), "currency": debt_currency, "description": description, "kind": debt_kind},
        )
        await db.refresh(debt)
        return {
            "id": str(debt.id),
            "kind": debt_kind,
            "amount": _money(debt.amount),
            "remaining": _money(debt.remaining_amount),
            "used": _money(debt.used_amount),
            "currency": debt.currency,
            "description": debt.description,
            "status": debt.status,
            "created_at": debt.created_at.isoformat() if debt.created_at else None,
            "paid_at": debt.paid_at.isoformat() if debt.paid_at else None,
        }


async def list_debts(user_id: int) -> list[dict[str, Any]]:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        current_group = await get_active_group_id(db, user)
        debts = (
            await db.execute(
                select(Debt)
                .where(Debt.user_id == user.id, Debt.group_id == current_group)
                .order_by(desc(Debt.created_at))
            )
        ).scalars().all()

        payload = []
        for debt in debts:
            debt_kind = normalize_debt_kind(getattr(debt, "kind", None))
            available = calculate_available_debt_source_native(debt)
            payload.append(
                {
                    "id": str(debt.id),
                    "kind": debt_kind,
                    "amount": _money(debt.amount),
                    "remaining": _money(debt.remaining_amount),
                    "used": _money(debt.used_amount),
                    "available_to_spend": _money(available),
                    "currency": debt.currency,
                    "description": debt.description,
                    "source_name": debt.source_name,
                    "source_contact": debt.source_contact,
                    "reference": debt.reference,
                    "note": debt.note,
                    "status": debt.status,
                    "created_at": debt.created_at.isoformat() if debt.created_at else None,
                    "paid_at": debt.paid_at.isoformat() if debt.paid_at else None,
                }
            )
        return payload


async def pay_debt(
    user_id: int,
    debt_id: str | UUID,
    amount: Decimal,
    currency: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    async with _session() as db:
        user = await _get_user_or_raise(db, user_id)
        current_group = await get_active_group_id(db, user)
        debt = (
            await db.execute(
                select(Debt).where(
                    Debt.id == UUID(str(debt_id)),
                    Debt.user_id == user.id,
                    Debt.group_id == current_group,
                )
            )
        ).scalar_one_or_none()
        if not debt:
            raise ValueError("Debt not found")

        payment_currency = normalize_currency(currency, user.default_currency)
        payment_amount = _money(amount)
        if payment_amount <= 0:
            raise ValueError("Amount must be positive")

        main_balance = await get_spendable_main_balance(db, user, payment_currency, current_group)
        if payment_amount > main_balance:
            raise ValueError(f"Insufficient main balance: {main_balance:.2f} {payment_currency}")

        repayment = await apply_debt_repayment(
            db,
            debt=debt,
            user=user,
            amount=payment_amount,
            currency=payment_currency,
            note=note,
        )
        db.add(
            Transaction(
                user_id=user.id,
                group_id=current_group,
                type=TransactionType.DEBT_PAYMENT,
                amount=payment_amount,
                currency=payment_currency,
                description=note or f"Debt repayment: {debt.description or debt.id}",
                funding_source="main",
                transaction_date=datetime.now(timezone.utc),
            )
        )
        await write_audit_log(
            db,
            action="debt.repaid",
            entity_type="debt",
            entity_id=str(debt.id),
            actor=user,
            group_id=current_group,
            payload={"amount": str(payment_amount), "currency": payment_currency},
        )
        await db.flush()
        await db.refresh(debt)
        return {
            "id": str(debt.id),
            "remaining": _money(debt.remaining_amount),
            "amount": _money(debt.amount),
            "currency": debt.currency,
            "status": debt.status,
            "repaid_amount": _money(repayment.amount),
            "repaid_at": repayment.repaid_at.isoformat() if repayment.repaid_at else None,
            "paid_at": debt.paid_at.isoformat() if debt.paid_at else None,
        }
