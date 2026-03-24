from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.auth import get_current_user
from config.admin import check_user_admin_status
from database.category_labels import present_category_name
from database.finance import get_exchange_rate, get_user_balance_summary, normalize_currency
from database.group_context import (
    get_active_group,
    is_group_admin,
    list_user_groups,
    normalize_lang,
    normalize_theme,
    set_active_group,
)
from database.models import Category, ExchangeRate, Group, User
from database.session import get_db

router = APIRouter()


class GroupOptionResponse(BaseModel):
    id: int
    name: str
    role: str
    joined_at: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    type: str
    icon: str
    is_system: bool


class BalanceResponse(BaseModel):
    total_balance: float
    own_balance: float
    received_balance: float
    debt_balance: float
    outstanding_debt_balance: float
    currency: str
    group_id: int
    group_name: str


class UserSettingsResponse(BaseModel):
    id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    language_code: str
    default_currency: str
    theme_preference: str
    active_group_id: Optional[int]
    active_group_name: Optional[str]
    groups: List[GroupOptionResponse]
    is_admin: bool
    is_group_admin: bool


class UpdateLanguageRequest(BaseModel):
    language: str = Field(..., pattern="^(uz|ru|en)$")


class UpdateCurrencyRequest(BaseModel):
    currency: str = Field(..., pattern="^(UZS|USD)$")


class UpdateThemeRequest(BaseModel):
    theme: str = Field(..., pattern="^(light|dark)$")


class UpdateActiveGroupRequest(BaseModel):
    group_id: int


class ExchangeRateResponse(BaseModel):
    from_currency: str
    to_currency: str
    rate: float
    updated_at: str


class UpdateExchangeRateRequest(BaseModel):
    rate: Decimal = Field(..., gt=0, description="Exchange rate must be positive")


async def build_user_settings_response(db: AsyncSession, current_user: User) -> dict:
    global_admin = await check_user_admin_status(current_user)
    active_group = await get_active_group(db, current_user)
    groups = await list_user_groups(db, current_user.id)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "language_code": normalize_lang(current_user.language_code),
        "default_currency": normalize_currency(current_user.default_currency, "UZS"),
        "theme_preference": normalize_theme(current_user.theme_preference),
        "active_group_id": active_group.id if active_group else None,
        "active_group_name": active_group.name if active_group else None,
        "groups": groups,
        "is_admin": global_admin,
        "is_group_admin": await is_group_admin(db, current_user, active_group.id if active_group else None),
    }


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(
    type: Optional[str] = Query(None, pattern="^(income|expense)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = normalize_lang(current_user.language_code)
    query = select(Category).where((Category.is_system.is_(True)) | (Category.user_id == current_user.id))

    if type:
        query = query.where(Category.type == type)

    categories = (await db.execute(query)).scalars().all()
    categories = sorted(
        categories,
        key=lambda cat: present_category_name(cat.name, lang, cat.is_system).lower(),
    )

    return [
        {
            "id": cat.id,
            "name": present_category_name(cat.name, lang, cat.is_system),
            "type": cat.type.value if hasattr(cat.type, "value") else str(cat.type),
            "icon": cat.icon,
            "is_system": cat.is_system,
        }
        for cat in categories
    ]


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await get_active_group(db, current_user)
    summary = await get_user_balance_summary(db, current_user, group_id=group.id)
    return {
        "total_balance": float(summary["total_balance"]),
        "own_balance": float(summary["own_balance"]),
        "received_balance": float(summary["received_balance"]),
        "debt_balance": float(summary["debt_balance"]),
        "outstanding_debt_balance": float(summary["outstanding_debt_balance"]),
        "currency": summary["currency"],
        "group_id": group.id,
        "group_name": group.name,
    }


@router.get("/user", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await build_user_settings_response(db, current_user)


@router.patch("/user/currency", response_model=UserSettingsResponse)
async def update_user_currency(
    request: UpdateCurrencyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    currency = normalize_currency(request.currency, "UZS")
    current_user.default_currency = currency
    await db.commit()
    await db.refresh(current_user)
    return await build_user_settings_response(db, current_user)


@router.patch("/user/language", response_model=UserSettingsResponse)
async def update_user_language(
    request: UpdateLanguageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    language = normalize_lang(request.language)
    current_user.language_code = language
    await db.commit()
    await db.refresh(current_user)
    return await build_user_settings_response(db, current_user)


@router.patch("/user/theme", response_model=UserSettingsResponse)
async def update_user_theme(
    request: UpdateThemeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    theme = normalize_theme(request.theme)
    current_user.theme_preference = theme
    await db.commit()
    await db.refresh(current_user)
    return await build_user_settings_response(db, current_user)


@router.patch("/user/active-group", response_model=UserSettingsResponse)
async def update_active_group(
    request: UpdateActiveGroupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        group = await set_active_group(db, current_user, request.group_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Group access denied")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    await db.commit()
    await db.refresh(current_user)
    return await build_user_settings_response(db, current_user)


@router.get("/exchange-rates", response_model=List[ExchangeRateResponse])
async def get_exchange_rates(db: AsyncSession = Depends(get_db)):
    await get_exchange_rate(db, "USD", "UZS")
    rates = (await db.execute(select(ExchangeRate))).scalars().all()
    return [
        {
            "from_currency": rate.from_currency,
            "to_currency": rate.to_currency,
            "rate": float(rate.rate),
            "updated_at": rate.updated_at.isoformat(),
        }
        for rate in rates
    ]


@router.get("/exchange-rate/{from_currency}/{to_currency}", response_model=ExchangeRateResponse)
async def read_exchange_rate(
    from_currency: str,
    to_currency: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        rate = await get_exchange_rate(db, from_currency, to_currency)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    result = await db.execute(
        select(ExchangeRate)
        .where(ExchangeRate.from_currency == normalize_currency(from_currency, "UZS"))
        .where(ExchangeRate.to_currency == normalize_currency(to_currency, "UZS"))
    )
    row = result.scalar_one_or_none()

    return {
        "from_currency": normalize_currency(from_currency, "UZS"),
        "to_currency": normalize_currency(to_currency, "UZS"),
        "rate": float(rate),
        "updated_at": row.updated_at.isoformat() if row else "",
    }


@router.patch("/exchange-rate/{from_currency}/{to_currency}")
async def update_exchange_rate(
    from_currency: str,
    to_currency: str,
    request: UpdateExchangeRateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await check_user_admin_status(current_user):
        raise HTTPException(status_code=403, detail="Only admins can update exchange rates")

    from_curr = normalize_currency(from_currency, "UZS")
    to_curr = normalize_currency(to_currency, "UZS")
    rate = request.rate

    direct = (
        await db.execute(
            select(ExchangeRate)
            .where(ExchangeRate.from_currency == from_curr)
            .where(ExchangeRate.to_currency == to_curr)
        )
    ).scalar_one_or_none()

    if direct:
        direct.rate = rate
        direct.updated_by = current_user.id
    else:
        db.add(
            ExchangeRate(
                from_currency=from_curr,
                to_currency=to_curr,
                rate=rate,
                updated_by=current_user.id,
            )
        )

    reverse_rate = (Decimal("1") / rate).quantize(Decimal("0.0000001"))
    reverse = (
        await db.execute(
            select(ExchangeRate)
            .where(ExchangeRate.from_currency == to_curr)
            .where(ExchangeRate.to_currency == from_curr)
        )
    ).scalar_one_or_none()

    if reverse:
        reverse.rate = reverse_rate
        reverse.updated_by = current_user.id
    else:
        db.add(
            ExchangeRate(
                from_currency=to_curr,
                to_currency=from_curr,
                rate=reverse_rate,
                updated_by=current_user.id,
            )
        )

    await db.commit()

    return {
        "success": True,
        "from_currency": from_curr,
        "to_currency": to_curr,
        "rate": float(rate),
    }
