from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.auth import get_current_user
from database.audit import write_audit_log
from database.finance import (
    apply_debt_repayment,
    convert_amount,
    get_available_debt_for_entry,
    get_spendable_main_balance,
    recalculate_debt_status,
)
from database.group_context import get_active_group_id
from database.models import Debt, Transaction, TransactionType, User
from database.session import get_db

router = APIRouter(prefix="/debts")


def _lang(value: str | None) -> str:
    lang = (value or "uz").split("-")[0].lower()
    return lang if lang in {"uz", "ru", "en"} else "uz"


def _t(lang: str, uz: str, ru: str, en: str) -> str:
    if lang == "ru":
        return ru
    if lang == "en":
        return en
    return uz


class DebtRepaymentResponse(BaseModel):
    id: str
    amount: float
    currency: str
    converted_amount: float
    note: Optional[str]
    repaid_at: str


class DebtCreateRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: Optional[str] = Field(None, pattern="^(UZS|USD)$")
    description: Optional[str] = None
    source_name: Optional[str] = None
    source_contact: Optional[str] = None
    reference: Optional[str] = None
    note: Optional[str] = None


class DebtResponse(BaseModel):
    id: str
    amount: float
    remaining: float
    used_amount: float
    available_to_spend: float
    currency: str
    status: str
    description: Optional[str] = None
    source_name: Optional[str] = None
    source_contact: Optional[str] = None
    reference: Optional[str] = None
    note: Optional[str] = None
    created_at: str
    paid_at: Optional[str] = None
    repayments: List[DebtRepaymentResponse] = []


class DebtPaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: Optional[str] = Field(None, pattern="^(UZS|USD)$")
    note: Optional[str] = None


async def _serialize_debt(
    db: AsyncSession,
    debt: Debt,
    target_currency: str,
) -> dict:
    available_to_spend = await get_available_debt_for_entry(db, debt, target_currency)
    repayments = []
    for repayment in sorted(debt.repayments, key=lambda item: item.repaid_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        amount_display = await convert_amount(db, repayment.amount, repayment.currency, target_currency)
        converted_display = await convert_amount(db, repayment.converted_amount, debt.currency, target_currency)
        repayments.append(
            {
                "id": str(repayment.id),
                "amount": float(amount_display),
                "currency": target_currency,
                "converted_amount": float(converted_display),
                "note": repayment.note,
                "repaid_at": repayment.repaid_at.isoformat(),
            }
        )

    amount_display = await convert_amount(db, debt.amount, debt.currency, target_currency)
    remaining_display = await convert_amount(db, debt.remaining_amount, debt.currency, target_currency)
    used_display = await convert_amount(db, debt.used_amount, debt.currency, target_currency)

    return {
        "id": str(debt.id),
        "amount": float(amount_display),
        "remaining": float(remaining_display),
        "used_amount": float(used_display),
        "available_to_spend": float(available_to_spend),
        "currency": target_currency,
        "status": debt.status,
        "description": debt.description,
        "source_name": debt.source_name,
        "source_contact": debt.source_contact,
        "reference": debt.reference,
        "note": debt.note,
        "created_at": debt.created_at.isoformat(),
        "paid_at": debt.paid_at.isoformat() if debt.paid_at else None,
        "repayments": repayments,
    }


@router.get("/", response_model=List[DebtResponse])
async def list_debts_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group_id = await get_active_group_id(db, current_user)
    debts = (
        await db.execute(
            select(Debt)
            .where(Debt.user_id == current_user.id, Debt.group_id == group_id)
            .order_by(desc(Debt.created_at))
        )
    ).scalars().unique().all()
    return [DebtResponse(**(await _serialize_debt(db, debt, current_user.default_currency))) for debt in debts]


@router.post("/", response_model=DebtResponse)
async def create_debt_endpoint(
    payload: DebtCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group_id = await get_active_group_id(db, current_user)
    currency = (payload.currency or current_user.default_currency).upper()

    debt = Debt(
        user_id=current_user.id,
        group_id=group_id,
        amount=payload.amount,
        remaining_amount=payload.amount,
        used_amount=Decimal("0.00"),
        currency=currency,
        description=payload.description,
        source_name=payload.source_name,
        source_contact=payload.source_contact,
        reference=payload.reference,
        note=payload.note,
        status="active",
    )
    db.add(debt)

    db.add(
        Transaction(
            user_id=current_user.id,
            group_id=group_id,
            type=TransactionType.DEBT,
            amount=payload.amount,
            currency=currency,
            description=payload.description or payload.source_name or "Debt created",
            funding_source="main",
        )
    )

    await write_audit_log(
        db,
        action="debt.created",
        entity_type="debt",
        entity_id=str(debt.id),
        actor=current_user,
        group_id=group_id,
        payload={
            "amount": str(payload.amount),
            "currency": currency,
            "source_name": payload.source_name,
        },
    )

    await db.commit()
    await db.refresh(debt)
    return DebtResponse(**(await _serialize_debt(db, debt, current_user.default_currency)))


@router.post("/{debt_id}/pay", response_model=DebtResponse)
async def pay_debt_endpoint(
    debt_id: UUID,
    payload: DebtPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    group_id = await get_active_group_id(db, current_user)

    debt = (
        await db.execute(
            select(Debt).where(
                Debt.id == debt_id,
                Debt.user_id == current_user.id,
                Debt.group_id == group_id,
            )
        )
    ).scalar_one_or_none()
    if not debt:
        raise HTTPException(status_code=404, detail=_t(lang, "Qarz topilmadi", "Долг не найден", "Debt not found"))
    if debt.status in {"fully_repaid", "archived"} or Decimal(str(debt.remaining_amount)) <= 0:
        raise HTTPException(
            status_code=400,
            detail=_t(lang, "Qarz yopilgan", "Долг уже закрыт", "Debt is already closed"),
        )

    payment_currency = (payload.currency or current_user.default_currency).upper()
    spendable_main = await get_spendable_main_balance(db, current_user, payment_currency, group_id)
    if payload.amount > spendable_main:
        raise HTTPException(
            status_code=400,
            detail=_t(
                lang,
                f"Asosiy balans yetarli emas. Mavjud: {spendable_main} {payment_currency}",
                f"Недостаточно основного баланса. Доступно: {spendable_main} {payment_currency}",
                f"Insufficient main balance. Available: {spendable_main} {payment_currency}",
            ),
        )

    repayment = await apply_debt_repayment(
        db,
        debt=debt,
        user=current_user,
        amount=payload.amount,
        currency=payment_currency,
        note=payload.note,
    )
    if Decimal(str(debt.remaining_amount)) <= 0 and not debt.paid_at:
        debt.paid_at = datetime.now(timezone.utc)
    recalculate_debt_status(debt)

    db.add(
        Transaction(
            user_id=current_user.id,
            group_id=group_id,
            type=TransactionType.DEBT_PAYMENT,
            amount=payload.amount,
            currency=payment_currency,
            description=payload.note or debt.description or "Debt repayment",
            funding_source="main",
        )
    )

    await write_audit_log(
        db,
        action="debt.repayment.created",
        entity_type="debt",
        entity_id=str(debt.id),
        actor=current_user,
        group_id=group_id,
        payload={
            "repayment_id": str(repayment.id),
            "amount": str(payload.amount),
            "currency": payment_currency,
            "converted_amount": str(repayment.converted_amount),
        },
    )

    await db.commit()
    await db.refresh(debt)
    return DebtResponse(**(await _serialize_debt(db, debt, current_user.default_currency)))
