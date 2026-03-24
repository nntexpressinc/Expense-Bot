from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.auth import get_current_user
from config.admin import check_user_admin_status
from database.audit import write_audit_log
from database.finance import convert_amount, get_user_balance_summary, normalize_currency
from database.group_context import (
    add_user_to_group,
    create_group_for_user,
    get_group_role,
    is_group_admin,
    list_user_groups,
    remove_user_from_group,
    rename_group,
)
from database.models import Debt, Transaction, User, UserGroup
from database.session import get_db

router = APIRouter(prefix="/groups", tags=["Groups"])


def _lang(value: str | None) -> str:
    lang = (value or "uz").split("-")[0].lower()
    return lang if lang in {"uz", "ru", "en"} else "uz"


def _t(lang: str, uz: str, ru: str, en: str) -> str:
    if lang == "ru":
        return ru
    if lang == "en":
        return en
    return uz


class GroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class GroupRenameRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class GroupMemberUpsertRequest(BaseModel):
    user_id: int
    role: str = Field("member", pattern="^(admin|member)$")


class GroupMemberResponse(BaseModel):
    user_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    role: str


class GroupUserOverviewItem(BaseModel):
    user_id: int
    display_name: str
    username: Optional[str]
    role: str
    currency: str
    total_balance: float
    debt_balance: float
    outstanding_debt_balance: float
    debt_count: int
    active_debt_count: int
    recent_transactions: list[dict]


@router.get("/")
async def get_my_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_user_groups(db, current_user.id)


@router.post("/")
async def create_group(
    payload: GroupCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await create_group_for_user(db, current_user, payload.name, set_as_active=False)
    await write_audit_log(
        db,
        action="group.created",
        entity_type="group",
        entity_id=str(group.id),
        actor=current_user,
        group_id=group.id,
        payload={"name": group.name},
    )
    await db.commit()
    return {"id": group.id, "name": group.name}


@router.patch("/{group_id}")
async def update_group_name(
    group_id: int,
    payload: GroupRenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    if not await is_group_admin(db, current_user, group_id):
        raise HTTPException(status_code=403, detail=_t(lang, "Ruxsat yo'q", "Доступ запрещён", "Access denied"))
    group = await rename_group(db, group_id, payload.name)
    await write_audit_log(
        db,
        action="group.renamed",
        entity_type="group",
        entity_id=str(group.id),
        actor=current_user,
        group_id=group.id,
        payload={"name": group.name},
    )
    await db.commit()
    return {"id": group.id, "name": group.name}


@router.get("/{group_id}/members", response_model=List[GroupMemberResponse])
async def list_group_members(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    if not await is_group_admin(db, current_user, group_id) and not await check_user_admin_status(current_user):
        raise HTTPException(status_code=403, detail=_t(lang, "Ruxsat yo'q", "Доступ запрещён", "Access denied"))

    rows = (
        await db.execute(
            select(UserGroup, User)
            .join(User, User.id == UserGroup.user_id)
            .where(UserGroup.group_id == group_id)
            .order_by(User.first_name.asc(), User.id.asc())
        )
    ).all()

    return [
        {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": membership.role,
        }
        for membership, user in rows
    ]


@router.post("/{group_id}/members")
async def upsert_group_member(
    group_id: int,
    payload: GroupMemberUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    if not await is_group_admin(db, current_user, group_id):
        raise HTTPException(status_code=403, detail=_t(lang, "Ruxsat yo'q", "Доступ запрещён", "Access denied"))

    target_user = (await db.execute(select(User).where(User.id == payload.user_id))).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail=_t(lang, "Foydalanuvchi topilmadi", "Пользователь не найден", "User not found"))

    membership = await add_user_to_group(db, target_user, group_id, payload.role)
    await write_audit_log(
        db,
        action="group.member.upserted",
        entity_type="group",
        entity_id=str(group_id),
        actor=current_user,
        group_id=group_id,
        payload={"user_id": payload.user_id, "role": membership.role},
    )
    await db.commit()
    return {"success": True, "user_id": payload.user_id, "role": membership.role}


@router.delete("/{group_id}/members/{user_id}")
async def delete_group_member(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    if not await is_group_admin(db, current_user, group_id):
        raise HTTPException(status_code=403, detail=_t(lang, "Ruxsat yo'q", "Доступ запрещён", "Access denied"))

    target_user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail=_t(lang, "Foydalanuvchi topilmadi", "Пользователь не найден", "User not found"))

    role = await get_group_role(db, user_id, group_id)
    if role == "admin" and user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail=_t(
                lang,
                "O'zingizni admin sifatida olib tashlay olmaysiz",
                "Нельзя удалить себя как администратора",
                "You cannot remove yourself as admin",
            ),
        )

    await remove_user_from_group(db, target_user, group_id)
    await write_audit_log(
        db,
        action="group.member.removed",
        entity_type="group",
        entity_id=str(group_id),
        actor=current_user,
        group_id=group_id,
        payload={"user_id": user_id},
    )
    await db.commit()
    return {"success": True}


@router.get("/{group_id}/overview", response_model=List[GroupUserOverviewItem])
async def get_group_user_overview(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    if not await is_group_admin(db, current_user, group_id) and not await check_user_admin_status(current_user):
        raise HTTPException(status_code=403, detail=_t(lang, "Ruxsat yo'q", "Доступ запрещён", "Access denied"))

    display_currency = normalize_currency(current_user.default_currency, "UZS")
    rows = (
        await db.execute(
            select(UserGroup, User)
            .join(User, User.id == UserGroup.user_id)
            .where(UserGroup.group_id == group_id)
            .order_by(User.first_name.asc(), User.id.asc())
        )
    ).all()

    response: list[dict] = []
    for membership, user in rows:
        balance = await get_user_balance_summary(
            db,
            user,
            target_currency=display_currency,
            group_id=group_id,
        )
        recent_transactions = (
            await db.execute(
                select(Transaction)
                .where(Transaction.user_id == user.id, Transaction.group_id == group_id)
                .order_by(desc(Transaction.transaction_date))
                .limit(5)
            )
        ).scalars().all()
        debts = (
            await db.execute(select(Debt).where(Debt.user_id == user.id, Debt.group_id == group_id))
        ).scalars().all()

        display_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or (f"@{user.username}" if user.username else str(user.id))
        response.append(
            {
                "user_id": user.id,
                "display_name": display_name,
                "username": user.username,
                "role": membership.role,
                "currency": display_currency,
                "total_balance": float(balance["total_balance"]),
                "debt_balance": float(balance["debt_balance"]),
                "outstanding_debt_balance": float(balance["outstanding_debt_balance"]),
                "debt_count": len(debts),
                "active_debt_count": sum(1 for debt in debts if debt.status in {"active", "partially_repaid"}),
                "recent_transactions": [
                    {
                        "id": str(item.id),
                        "type": item.type.value if hasattr(item.type, "value") else str(item.type),
                        "amount": float(await convert_amount(db, item.amount, item.currency, display_currency)),
                        "currency": display_currency,
                        "description": item.description or "-",
                        "date": item.transaction_date.isoformat(),
                    }
                    for item in recent_transactions
                ],
            }
        )

    return response
