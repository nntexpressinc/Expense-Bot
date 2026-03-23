"""
SQLAlchemy models for Expenses Bot.

The schema keeps backward compatibility with the original user-centric design,
but adds production-facing foundations:
- many-to-many user-group memberships with active group selection
- group-scoped finance data isolation
- debt usage and repayment history
- worker / attendance / payroll records
- audit logs for sensitive actions
"""

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Numeric,
    Text,
    Boolean,
    DateTime,
    Date,
    Time,
    Integer,
    ForeignKey,
    Enum as SQLEnum,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, ENUM as PGEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, date
import uuid
import enum

from database.session import Base


# Enums
class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    DEBT = "debt"
    DEBT_PAYMENT = "debt_payment"


class TransferStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class NotificationType(str, enum.Enum):
    DAILY_REMINDER = "daily_reminder"
    TRANSFER_RECEIVED = "transfer_received"
    TRANSFER_SPENT = "transfer_spent"
    BUDGET_WARNING = "budget_warning"


class ReportType(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    EXCEL = "excel"


def _pg_enum(enum_cls: type[enum.Enum], name: str) -> SQLEnum:
    return PGEnum(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


TRANSACTION_TYPE_ENUM = _pg_enum(TransactionType, "transaction_type")
TRANSFER_STATUS_ENUM = _pg_enum(TransferStatus, "transfer_status")
CATEGORY_TYPE_ENUM = _pg_enum(CategoryType, "category_type")
NOTIFICATION_TYPE_ENUM = _pg_enum(NotificationType, "notification_type")
REPORT_TYPE_ENUM = _pg_enum(ReportType, "report_type")
REPORT_FORMAT_ENUM = _pg_enum(ReportFormat, "report_format")


class Group(Base):
    """Logical workspace. A user may belong to multiple groups."""

    __tablename__ = "groups"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    memberships = relationship("UserGroup", back_populates="group", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="group")
    transfers = relationship("Transfer", back_populates="group")
    debts = relationship("Debt", back_populates="group")
    workers = relationship("Worker", back_populates="group", cascade="all, delete-orphan")
    payroll_periods = relationship("PayrollPeriod", back_populates="group", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Group {self.id} {self.name}>"


class User(Base):
    """Telegram user."""

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, comment="Telegram User ID")
    # Legacy field kept for compatibility with previous versions and migrations.
    group_id = Column(BigInteger, nullable=True, index=True)
    active_group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="ru")
    default_currency = Column(String(3), default="UZS")
    theme_preference = Column(String(20), nullable=False, default="light")
    is_active = Column(Boolean, default=True)
    # Global/super admin flag. Group-specific permissions live in user_groups.role.
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    sent_transfers = relationship("Transfer", foreign_keys="Transfer.sender_id", back_populates="sender")
    received_transfers = relationship("Transfer", foreign_keys="Transfer.recipient_id", back_populates="recipient")
    balance = relationship("Balance", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    custom_categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    memberships = relationship("UserGroup", back_populates="user", cascade="all, delete-orphan")
    active_group = relationship("Group", foreign_keys=[active_group_id])

    def __repr__(self):
        return f"<User {self.id} @{self.username}>"


class UserGroup(Base):
    """Many-to-many user-group relation with per-group role."""

    __tablename__ = "user_groups"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(20), nullable=False, default="member", index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="memberships")
    group = relationship("Group", back_populates="memberships")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'member')", name="valid_group_role"),
    )

    def __repr__(self):
        return f"<UserGroup user={self.user_id} group={self.group_id} role={self.role}>"


class Category(Base):
    """Category model."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    type = Column(CATEGORY_TYPE_ENUM, nullable=False)
    icon = Column(String(10), nullable=True)
    is_system = Column(Boolean, default=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="custom_categories")
    transactions = relationship("Transaction", back_populates="category")
    transfer_expenses = relationship("TransferExpense", back_populates="category")

    __table_args__ = (
        UniqueConstraint("name", "type", "user_id", name="unique_system_category"),
    )

    def __repr__(self):
        return f"<Category {self.id} {self.icon} {self.name}>"


class Transaction(Base):
    """Financial transaction."""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    type = Column(TRANSACTION_TYPE_ENUM, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="UZS")
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    funding_source = Column(String(20), nullable=False, default="main", index=True)
    attachment_file_id = Column(String(512), nullable=True)
    attachment_type = Column(String(20), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    transfer_id = Column(UUID(as_uuid=True), ForeignKey("transfers.id", ondelete="SET NULL"), nullable=True, index=True)
    transaction_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="transactions")
    group = relationship("Group", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    transfer = relationship("Transfer", back_populates="transactions")
    transfer_expense = relationship("TransferExpense", back_populates="transaction", uselist=False)
    debt_usage = relationship("DebtUsage", back_populates="transaction", uselist=False)

    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint("funding_source IN ('main', 'debt')", name="valid_funding_source"),
    )

    def __repr__(self):
        return f"<Transaction {self.id} {self.type.value} {self.amount} {self.currency}>"


class Transfer(Base):
    """Peer-to-peer internal transfer."""

    __tablename__ = "transfers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    sender_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="UZS")
    description = Column(Text, nullable=True)
    status = Column(TRANSFER_STATUS_ENUM, nullable=False, default=TransferStatus.PENDING, index=True)
    remaining_amount = Column(Numeric(15, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    group = relationship("Group", back_populates="transfers")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_transfers")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_transfers")
    transactions = relationship("Transaction", back_populates="transfer")
    expenses = relationship("TransferExpense", back_populates="transfer", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_transfer_amount"),
        CheckConstraint("sender_id != recipient_id", name="no_self_transfer"),
        CheckConstraint("remaining_amount >= 0 AND remaining_amount <= amount", name="remaining_amount_valid"),
    )

    def __repr__(self):
        return f"<Transfer {self.id} {self.sender_id}->{self.recipient_id} {self.amount} {self.currency}>"


class TransferExpense(Base):
    """Expense allocation against incoming transfer budget."""

    __tablename__ = "transfer_expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    transfer_id = Column(UUID(as_uuid=True), ForeignKey("transfers.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True)
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    transfer = relationship("Transfer", back_populates="expenses")
    transaction = relationship("Transaction", back_populates="transfer_expense")
    category = relationship("Category", back_populates="transfer_expenses")

    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_expense_amount"),
    )

    def __repr__(self):
        return f"<TransferExpense {self.id} {self.amount}>"


class Balance(Base):
    """Legacy balance snapshot table. Kept for compatibility."""

    __tablename__ = "balances"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    currency = Column(String(3), nullable=False, default="UZS")
    total_balance = Column(Numeric(15, 2), nullable=False, default=0)
    own_balance = Column(Numeric(15, 2), nullable=False, default=0)
    received_balance = Column(Numeric(15, 2), nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)

    user = relationship("User", back_populates="balance")

    def __repr__(self):
        return f"<Balance user_id={self.user_id} total={self.total_balance} {self.currency}>"


class Debt(Base):
    """Borrowed money entry. Supports usage + repayment history."""

    __tablename__ = "debts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    remaining_amount = Column(Numeric(15, 2), nullable=False)
    used_amount = Column(Numeric(15, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="UZS")
    description = Column(Text, nullable=True)
    source_name = Column(String(255), nullable=True)
    source_contact = Column(String(255), nullable=True)
    reference = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    group = relationship("Group", back_populates="debts")
    usages = relationship("DebtUsage", back_populates="debt", cascade="all, delete-orphan")
    repayments = relationship("DebtRepayment", back_populates="debt", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_debt_amount"),
        CheckConstraint("remaining_amount >= 0", name="non_negative_remaining_debt"),
        CheckConstraint("used_amount >= 0", name="non_negative_used_debt"),
        CheckConstraint("used_amount <= amount", name="used_amount_within_principal"),
        CheckConstraint(
            "status IN ('active', 'partially_repaid', 'fully_repaid', 'archived')",
            name="valid_debt_status",
        ),
    )

    def __repr__(self):
        return f"<Debt {self.id} user={self.user_id} {self.remaining_amount}/{self.amount} {self.currency}>"


class DebtUsage(Base):
    """Which expense consumed which debt source."""

    __tablename__ = "debt_usages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    debt_id = Column(UUID(as_uuid=True), ForeignKey("debts.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="UZS")
    note = Column(Text, nullable=True)
    used_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    debt = relationship("Debt", back_populates="usages")
    transaction = relationship("Transaction", back_populates="debt_usage")

    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_debt_usage_amount"),
    )


class DebtRepayment(Base):
    """Repayment history against a debt entry."""

    __tablename__ = "debt_repayments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    debt_id = Column(UUID(as_uuid=True), ForeignKey("debts.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="UZS")
    converted_amount = Column(Numeric(15, 2), nullable=False)
    note = Column(Text, nullable=True)
    repaid_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    debt = relationship("Debt", back_populates="repayments")
    user = relationship("User")

    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_debt_repayment_amount"),
        CheckConstraint("converted_amount > 0", name="positive_debt_repayment_converted_amount"),
    )


class Notification(Base):
    """Notification settings model."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(NOTIFICATION_TYPE_ENUM, nullable=False)
    enabled = Column(Boolean, default=True, index=True)
    time = Column(Time, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        UniqueConstraint("user_id", "type", name="unique_user_notification"),
    )

    def __repr__(self):
        return f"<Notification {self.id} user={self.user_id} type={self.type.value}>"


class Report(Base):
    """Generated report metadata."""

    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(REPORT_TYPE_ENUM, nullable=False)
    format = Column(REPORT_FORMAT_ENUM, nullable=False)
    file_path = Column(String(500), nullable=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="reports")

    __table_args__ = (
        CheckConstraint("period_end >= period_start", name="valid_period"),
    )

    def __repr__(self):
        return f"<Report {self.id} {self.type.value} {self.format.value}>"


class ExchangeRate(Base):
    """Exchange rate model."""

    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_currency = Column(String(3), nullable=False, index=True)
    to_currency = Column(String(3), nullable=False, index=True)
    rate = Column(Numeric(15, 6), nullable=False)
    updated_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)

    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", name="unique_exchange_pair"),
        CheckConstraint("rate > 0", name="positive_rate"),
    )

    def __repr__(self):
        return f"<ExchangeRate {self.from_currency}->{self.to_currency} {self.rate}>"


class Worker(Base):
    """Worker/employee scoped to a group."""

    __tablename__ = "workers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    role_name = Column(String(255), nullable=True)
    payment_type = Column(String(20), nullable=False, default="daily", index=True)
    rate = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="UZS")
    start_date = Column(Date, nullable=False, default=date.today, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    notes = Column(Text, nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    group = relationship("Group", back_populates="workers")
    attendance_entries = relationship("AttendanceEntry", back_populates="worker", cascade="all, delete-orphan")
    advances = relationship("WorkerAdvance", back_populates="worker", cascade="all, delete-orphan")
    payments = relationship("WorkerPayment", back_populates="worker", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("payment_type IN ('daily', 'monthly', 'volume')", name="valid_worker_payment_type"),
        CheckConstraint("rate >= 0", name="non_negative_worker_rate"),
    )


class AttendanceEntry(Base):
    """Minimal attendance/output tracking."""

    __tablename__ = "attendance_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="present", index=True)
    units = Column(Numeric(15, 2), nullable=False, default=0)
    comment = Column(Text, nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    worker = relationship("Worker", back_populates="attendance_entries")

    __table_args__ = (
        UniqueConstraint("worker_id", "entry_date", name="unique_worker_attendance_date"),
        CheckConstraint("status IN ('present', 'absent', 'half_day', 'custom')", name="valid_attendance_status"),
        CheckConstraint("units >= 0", name="non_negative_attendance_units"),
    )


class PayrollPeriod(Base):
    """Payroll period definition."""

    __tablename__ = "payroll_periods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    finalized_at = Column(DateTime(timezone=True), nullable=True)

    group = relationship("Group", back_populates="payroll_periods")
    payments = relationship("WorkerPayment", back_populates="payroll_period")

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="valid_payroll_period_dates"),
        CheckConstraint("status IN ('open', 'finalized', 'paid')", name="valid_payroll_period_status"),
    )


class WorkerAdvance(Base):
    """Advance paid before final payroll."""

    __tablename__ = "worker_advances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="UZS")
    note = Column(Text, nullable=True)
    payment_date = Column(Date, nullable=False, default=date.today, index=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    worker = relationship("Worker", back_populates="advances")

    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_worker_advance_amount"),
    )


class WorkerPayment(Base):
    """Payout made to worker."""

    __tablename__ = "worker_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    payroll_period_id = Column(UUID(as_uuid=True), ForeignKey("payroll_periods.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="UZS")
    note = Column(Text, nullable=True)
    payment_date = Column(Date, nullable=False, default=date.today, index=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    worker = relationship("Worker", back_populates="payments")
    payroll_period = relationship("PayrollPeriod", back_populates="payments")

    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_worker_payment_amount"),
    )


class AuditLog(Base):
    """Append-only audit trail for finance/admin actions."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    actor_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(255), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    group = relationship("Group", back_populates="audit_logs")
