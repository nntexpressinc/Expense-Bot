from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.auth import get_current_user
from database.audit import write_audit_log
from database.finance import get_spendable_main_balance, normalize_currency
from database.group_context import get_active_group_id, user_has_group_access
from database.models import AttendanceEntry, Transaction, TransactionType, User, Worker, WorkerAdvance, WorkerPayment
from database.session import get_db
from database.workers import calculate_group_payroll_summary, calculate_worker_period_summary

router = APIRouter(prefix="/workers", tags=["Workers"])


def _lang(value: str | None) -> str:
    lang = (value or "uz").split("-")[0].lower()
    return lang if lang in {"uz", "ru", "en"} else "uz"


def _t(lang: str, uz: str, ru: str, en: str) -> str:
    if lang == "ru":
        return ru
    if lang == "en":
        return en
    return uz


async def _require_workers_access(db: AsyncSession, current_user: User, group_id: int) -> None:
    lang = _lang(current_user.language_code)
    if not await user_has_group_access(db, current_user.id, group_id):
        raise HTTPException(status_code=403, detail=_t(lang, "Ruxsat yo'q", "Доступ запрещён", "Access denied"))


class WorkerCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    role_name: Optional[str] = None
    payment_type: str = Field(..., pattern="^(daily|monthly|volume)$")
    rate: Decimal = Field(..., ge=0)
    currency: Optional[str] = Field(None, pattern="^(UZS|USD)$")
    start_date: date
    notes: Optional[str] = None


class AttendanceCreateRequest(BaseModel):
    entry_date: date
    status: str = Field(..., pattern="^(present|absent|half_day|custom)$")
    units: Decimal = Field(Decimal("0"), ge=0)
    comment: Optional[str] = None


class WorkerMoneyRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: Optional[str] = Field(None, pattern="^(UZS|USD)$")
    note: Optional[str] = None
    payment_date: date = Field(default_factory=date.today)


class WorkerResponse(BaseModel):
    id: str
    full_name: str
    phone: Optional[str]
    role_name: Optional[str]
    payment_type: str
    rate: float
    currency: str
    start_date: str
    is_active: bool
    notes: Optional[str]
    today_status: Optional[str] = None
    today_units: float = 0.0


class AttendanceListItem(BaseModel):
    id: str
    worker_id: str
    worker_name: str
    entry_date: str
    status: str
    units: float
    comment: Optional[str] = None


def _month_range(target_date: date) -> tuple[date, date]:
    start = target_date.replace(day=1)
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = next_month - timedelta(days=1)
    return start, end


@router.get("/", response_model=List[WorkerResponse])
async def list_workers(
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group_id = await get_active_group_id(db, current_user)
    await _require_workers_access(db, current_user, group_id)
    query = select(Worker).where(Worker.group_id == group_id)
    if not include_inactive:
        query = query.where(Worker.is_active.is_(True))
    workers = (await db.execute(query.order_by(Worker.full_name.asc()))).scalars().all()
    today = date.today()
    attendance_rows = []
    if workers:
        attendance_rows = (
            await db.execute(
                select(AttendanceEntry).where(
                    AttendanceEntry.group_id == group_id,
                    AttendanceEntry.entry_date == today,
                    AttendanceEntry.worker_id.in_([worker.id for worker in workers]),
                )
            )
        ).scalars().all()
    today_map = {entry.worker_id: entry for entry in attendance_rows}
    return [
        {
            "id": str(worker.id),
            "full_name": worker.full_name,
            "phone": worker.phone,
            "role_name": worker.role_name,
            "payment_type": worker.payment_type,
            "rate": float(worker.rate),
            "currency": worker.currency,
            "start_date": worker.start_date.isoformat(),
            "is_active": worker.is_active,
            "notes": worker.notes,
            "today_status": today_map.get(worker.id).status if today_map.get(worker.id) else None,
            "today_units": float(today_map.get(worker.id).units or 0) if today_map.get(worker.id) else 0.0,
        }
        for worker in workers
    ]


@router.get("/attendance", response_model=List[AttendanceListItem])
async def list_attendance_entries(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=300),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group_id = await get_active_group_id(db, current_user)
    await _require_workers_access(db, current_user, group_id)

    today = date.today()
    resolved_start = start_date or today.replace(day=1)
    resolved_end = end_date or today

    rows = (
        await db.execute(
            select(AttendanceEntry, Worker)
            .join(Worker, Worker.id == AttendanceEntry.worker_id)
            .where(
                AttendanceEntry.group_id == group_id,
                AttendanceEntry.entry_date >= resolved_start,
                AttendanceEntry.entry_date <= resolved_end,
            )
            .order_by(desc(AttendanceEntry.entry_date), Worker.full_name.asc())
            .limit(limit)
        )
    ).all()

    return [
        {
            "id": str(entry.id),
            "worker_id": str(worker.id),
            "worker_name": worker.full_name,
            "entry_date": entry.entry_date.isoformat(),
            "status": entry.status,
            "units": float(entry.units or 0),
            "comment": entry.comment,
        }
        for entry, worker in rows
    ]


@router.post("/", response_model=WorkerResponse)
async def create_worker(
    payload: WorkerCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    group_id = await get_active_group_id(db, current_user)
    if not await user_has_group_access(db, current_user.id, group_id):
        raise HTTPException(status_code=403, detail=_t(lang, "Ruxsat yo'q", "Доступ запрещён", "Access denied"))

    worker = Worker(
        group_id=group_id,
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        role_name=payload.role_name,
        payment_type=payload.payment_type,
        rate=payload.rate,
        currency=normalize_currency(payload.currency, current_user.default_currency),
        start_date=payload.start_date,
        notes=payload.notes,
        created_by=current_user.id,
        is_active=True,
    )
    db.add(worker)
    await write_audit_log(
        db,
        action="worker.created",
        entity_type="worker",
        entity_id=str(worker.id),
        actor=current_user,
        group_id=group_id,
        payload={"full_name": payload.full_name, "payment_type": payload.payment_type},
    )
    await db.commit()
    await db.refresh(worker)
    return {
        "id": str(worker.id),
        "full_name": worker.full_name,
        "phone": worker.phone,
        "role_name": worker.role_name,
        "payment_type": worker.payment_type,
        "rate": float(worker.rate),
        "currency": worker.currency,
        "start_date": worker.start_date.isoformat(),
        "is_active": worker.is_active,
        "notes": worker.notes,
    }


@router.post("/{worker_id}/attendance")
async def record_attendance(
    worker_id: UUID,
    payload: AttendanceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    group_id = await get_active_group_id(db, current_user)
    await _require_workers_access(db, current_user, group_id)

    worker = (
        await db.execute(select(Worker).where(Worker.id == worker_id, Worker.group_id == group_id))
    ).scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail=_t(lang, "Ishchi topilmadi", "Сотрудник не найден", "Worker not found"))

    entry = (
        await db.execute(
            select(AttendanceEntry).where(
                AttendanceEntry.worker_id == worker_id,
                AttendanceEntry.entry_date == payload.entry_date,
            )
        )
    ).scalar_one_or_none()
    if not entry:
        entry = AttendanceEntry(
            worker_id=worker_id,
            group_id=group_id,
            entry_date=payload.entry_date,
            status=payload.status,
            units=payload.units,
            comment=payload.comment,
            created_by=current_user.id,
        )
        db.add(entry)
    else:
        entry.status = payload.status
        entry.units = payload.units
        entry.comment = payload.comment

    await write_audit_log(
        db,
        action="worker.attendance.upserted",
        entity_type="worker",
        entity_id=str(worker_id),
        actor=current_user,
        group_id=group_id,
        payload={"entry_date": payload.entry_date.isoformat(), "status": payload.status, "units": str(payload.units)},
    )
    await db.commit()
    return {"success": True}


async def _create_worker_money_record(
    *,
    db: AsyncSession,
    current_user: User,
    worker: Worker,
    payload: WorkerMoneyRequest,
    record_type: str,
):
    group_id = worker.group_id
    lang = _lang(current_user.language_code)
    currency = normalize_currency(payload.currency, current_user.default_currency)
    main_balance = await get_spendable_main_balance(db, current_user, currency, group_id)
    if payload.amount > main_balance:
        raise HTTPException(
            status_code=400,
            detail=_t(
                lang,
                f"Asosiy balans yetarli emas. Mavjud: {main_balance} {currency}",
                f"Недостаточно основного баланса. Доступно: {main_balance} {currency}",
                f"Insufficient main balance. Available: {main_balance} {currency}",
            ),
        )

    if record_type == "payment":
        start_date, end_date = _month_range(payload.payment_date)
        payable_summary = await calculate_worker_period_summary(
            db,
            worker,
            start_date,
            end_date,
            currency,
        )
        payable_amount = Decimal(str(payable_summary["payable_amount"]))
        if payable_amount <= 0:
            raise HTTPException(
                status_code=400,
                detail=_t(
                    lang,
                    "Bu ishchi uchun to'lanadigan summa yo'q",
                    "Для этого сотрудника нет суммы к выплате",
                    "There is no payable amount for this worker",
                ),
            )
        if payload.amount > payable_amount:
            raise HTTPException(
                status_code=400,
                detail=_t(
                    lang,
                    f"To'lov summasi oshib ketdi. Maksimal: {payable_amount} {currency}",
                    f"Сумма выплаты слишком большая. Максимум: {payable_amount} {currency}",
                    f"Payment amount is too high. Maximum: {payable_amount} {currency}",
                ),
            )

    duplicate_payment = (
        await db.execute(
            select(WorkerPayment if record_type == "payment" else WorkerAdvance).where(
                and_(
                    (WorkerPayment.worker_id if record_type == "payment" else WorkerAdvance.worker_id) == worker.id,
                    (WorkerPayment.amount if record_type == "payment" else WorkerAdvance.amount) == payload.amount,
                    (WorkerPayment.payment_date if record_type == "payment" else WorkerAdvance.payment_date) == payload.payment_date,
                    (WorkerPayment.note if record_type == "payment" else WorkerAdvance.note) == payload.note,
                )
            )
        )
    ).scalar_one_or_none()
    if duplicate_payment:
        raise HTTPException(
            status_code=409,
            detail=_t(
                lang,
                "Bir xil to'lov allaqachon yozilgan",
                "Похожая выплата уже существует",
                "A similar payment already exists",
            ),
        )

    if record_type == "payment":
        record = WorkerPayment(
            worker_id=worker.id,
            group_id=group_id,
            amount=payload.amount,
            currency=currency,
            note=payload.note,
            payment_date=payload.payment_date,
            created_by=current_user.id,
        )
    else:
        record = WorkerAdvance(
            worker_id=worker.id,
            group_id=group_id,
            amount=payload.amount,
            currency=currency,
            note=payload.note,
            payment_date=payload.payment_date,
            created_by=current_user.id,
        )
    db.add(record)

    db.add(
        Transaction(
            user_id=current_user.id,
            group_id=group_id,
            type=TransactionType.EXPENSE,
            amount=payload.amount,
            currency=currency,
            description=payload.note or f"Worker {record_type}: {worker.full_name}",
            funding_source="main",
        )
    )

    await write_audit_log(
        db,
        action=f"worker.{record_type}.created",
        entity_type="worker",
        entity_id=str(worker.id),
        actor=current_user,
        group_id=group_id,
        payload={"amount": str(payload.amount), "currency": currency, "payment_date": payload.payment_date.isoformat()},
    )
    await db.commit()
    return {"success": True}


@router.post("/{worker_id}/advances")
async def record_worker_advance(
    worker_id: UUID,
    payload: WorkerMoneyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    group_id = await get_active_group_id(db, current_user)
    await _require_workers_access(db, current_user, group_id)
    worker = (await db.execute(select(Worker).where(Worker.id == worker_id, Worker.group_id == group_id))).scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail=_t(lang, "Ishchi topilmadi", "Сотрудник не найден", "Worker not found"))
    return await _create_worker_money_record(db=db, current_user=current_user, worker=worker, payload=payload, record_type="advance")


@router.post("/{worker_id}/payments")
async def record_worker_payment(
    worker_id: UUID,
    payload: WorkerMoneyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    group_id = await get_active_group_id(db, current_user)
    await _require_workers_access(db, current_user, group_id)
    worker = (await db.execute(select(Worker).where(Worker.id == worker_id, Worker.group_id == group_id))).scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail=_t(lang, "Ishchi topilmadi", "Сотрудник не найден", "Worker not found"))
    return await _create_worker_money_record(db=db, current_user=current_user, worker=worker, payload=payload, record_type="payment")


@router.get("/summary")
async def get_payroll_summary(
    start_date: date,
    end_date: date,
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group_id = await get_active_group_id(db, current_user)
    await _require_workers_access(db, current_user, group_id)
    summary = await calculate_group_payroll_summary(
        db,
        group_id=group_id,
        start_date=start_date,
        end_date=end_date,
        target_currency=current_user.default_currency,
        include_inactive=include_inactive,
    )
    return summary


@router.get("/{worker_id}/summary")
async def get_worker_summary(
    worker_id: UUID,
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    group_id = await get_active_group_id(db, current_user)
    await _require_workers_access(db, current_user, group_id)
    worker = (await db.execute(select(Worker).where(Worker.id == worker_id, Worker.group_id == group_id))).scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail=_t(lang, "Ishchi topilmadi", "Сотрудник не найден", "Worker not found"))
    return await calculate_worker_period_summary(db, worker, start_date, end_date, current_user.default_currency)
