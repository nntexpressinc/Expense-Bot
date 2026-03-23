from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.auth import get_current_user
from bot.services.notifications import notify_transfer_participants
from database.finance import convert_amount, get_user_balance_summary, normalize_currency
from database.group_context import get_active_group_id, group_user_ids_query
from database.models import (
    Category,
    Transaction,
    TransactionType,
    Transfer,
    TransferExpense,
    TransferStatus,
    User,
    UserGroup,
)
from database.session import get_db

router = APIRouter()


def _lang(value: str | None) -> str:
    lang = (value or 'uz').split('-')[0].lower()
    return lang if lang in {'uz', 'ru', 'en'} else 'uz'


def _t(lang: str, uz: str, ru: str, en: str) -> str:
    if lang == 'ru':
        return ru
    if lang == 'en':
        return en
    return uz


def _display_user_ref(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if full_name:
        return full_name
    return str(user.id)


class TransferCreate(BaseModel):
    recipient_telegram_id: Optional[int] = None
    recipient_username: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: Optional[str] = None
    description: Optional[str] = None


class TransferRecipientResponse(BaseModel):
    id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    display_name: str


class TransferExpenseResponse(BaseModel):
    id: str
    amount: float
    currency: str
    category: dict
    description: Optional[str]
    created_at: datetime


class TransferResponse(BaseModel):
    id: UUID
    sender_id: int
    recipient_id: int
    recipient_username: Optional[str]
    recipient_name: Optional[str] = None
    amount: float
    remaining_amount: float
    currency: str
    status: str
    description: Optional[str]
    created_at: datetime
    original_amount: Optional[float] = None
    original_currency: Optional[str] = None
    expenses: Optional[List[TransferExpenseResponse]] = None


class TransferGroupResponse(BaseModel):
    recipient_id: int
    recipient_username: Optional[str]
    recipient_name: str
    transfer_count: int
    amount: float
    remaining_amount: float
    spent_amount: float
    currency: str
    last_transfer_at: datetime


class TransferGroupHistoryResponse(BaseModel):
    id: UUID
    amount: float
    remaining_amount: float
    spent_amount: float
    currency: str
    status: str
    description: Optional[str]
    created_at: datetime


class TransferGroupExpenseResponse(BaseModel):
    id: str
    transfer_id: str
    amount: float
    currency: str
    category: dict
    description: Optional[str]
    created_at: datetime


class TransferGroupDetailResponse(BaseModel):
    recipient_id: int
    recipient_username: Optional[str]
    recipient_name: str
    transfer_count: int
    amount: float
    remaining_amount: float
    spent_amount: float
    currency: str
    last_transfer_at: datetime
    transfers: List[TransferGroupHistoryResponse]
    expenses: List[TransferGroupExpenseResponse]


async def _resolve_recipient(
    db: AsyncSession,
    requester: User,
    payload: TransferCreate,
    lang: str,
) -> User:
    requester_group = await get_active_group_id(db, requester)
    group_members = group_user_ids_query(requester_group)

    if payload.recipient_telegram_id:
        recipient = (
            await db.execute(
                select(User).where(
                    User.id == payload.recipient_telegram_id,
                    User.id.in_(group_members),
                    User.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if recipient:
            return recipient

    if payload.recipient_username:
        username = payload.recipient_username.strip().lstrip('@')
        if username:
            recipient = (
                await db.execute(
                    select(User).where(
                        func.lower(User.username) == username.lower(),
                        User.id.in_(group_user_ids_query(requester_group)),
                        User.is_active.is_(True),
                    )
                )
            ).scalar_one_or_none()
            if recipient:
                return recipient

    raise HTTPException(
        status_code=404,
        detail=_t(
            lang,
            "Qabul qiluvchi topilmadi. @username yoki ID kiriting.",
            "Получатель не найден. Укажите @username или ID.",
            "Recipient not found. Send @username or ID.",
        ),
    )


async def _serialize_transfer_for_user(
    db: AsyncSession,
    transfer: Transfer,
    viewer: User,
    with_expenses: bool = False,
    counterpart_user: Optional[User] = None,
) -> dict:
    display_currency = normalize_currency(viewer.default_currency, 'UZS')
    lang = _lang(viewer.language_code)
    display_amount = await convert_amount(db, transfer.amount, transfer.currency, display_currency)
    display_remaining = await convert_amount(
        db,
        transfer.remaining_amount,
        transfer.currency,
        display_currency,
    )

    payload = {
        'id': transfer.id,
        'sender_id': transfer.sender_id,
        'recipient_id': transfer.recipient_id,
        'recipient_username': counterpart_user.username if counterpart_user else None,
        'recipient_name': _display_user_ref(counterpart_user) if counterpart_user else None,
        'amount': float(display_amount),
        'remaining_amount': float(display_remaining),
        'currency': display_currency,
        'status': transfer.status.value if hasattr(transfer.status, 'value') else str(transfer.status),
        'description': transfer.description,
        'created_at': transfer.created_at,
        'original_amount': float(transfer.amount),
        'original_currency': transfer.currency,
    }

    if not with_expenses:
        return payload

    expenses = (
        await db.execute(
            select(TransferExpense)
            .where(TransferExpense.transfer_id == transfer.id)
            .order_by(desc(TransferExpense.created_at))
        )
    ).scalars().all()

    expense_rows = []
    for exp in expenses:
        category = None
        if exp.category_id:
            category = (
                await db.execute(select(Category).where(Category.id == exp.category_id))
            ).scalar_one_or_none()

        amount_display = await convert_amount(
            db,
            exp.amount,
            transfer.currency,
            display_currency,
        )

        expense_rows.append(
            {
                'id': str(exp.id),
                'amount': float(amount_display),
                'currency': display_currency,
                'category': {
                    'id': category.id if category else None,
                    'name': category.name if category else _t(lang, "Noma'lum", 'Неизвестно', 'Unknown'),
                    'icon': category.icon if category else '💰',
                },
                'description': exp.description,
                'created_at': exp.created_at,
            }
        )

    payload['expenses'] = expense_rows
    return payload


@router.get('/sent', response_model=list[TransferResponse])
async def get_sent_transfers(
    limit: int = Query(20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transfers = (
        await db.execute(
            select(Transfer)
            .where(Transfer.sender_id == current_user.id)
            .where(Transfer.group_id == await get_active_group_id(db, current_user))
            .order_by(desc(Transfer.created_at))
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    response = []
    for transfer in transfers:
        recipient = (
            await db.execute(select(User).where(User.id == transfer.recipient_id))
        ).scalar_one_or_none()
        response.append(
            await _serialize_transfer_for_user(
                db,
                transfer,
                current_user,
                with_expenses=False,
                counterpart_user=recipient,
            )
        )

    return response


@router.get('/sent/grouped', response_model=list[TransferGroupResponse])
async def get_sent_transfers_grouped(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    display_currency = normalize_currency(current_user.default_currency, 'UZS')
    transfers = (
        await db.execute(
            select(Transfer)
            .where(Transfer.sender_id == current_user.id)
            .where(Transfer.group_id == await get_active_group_id(db, current_user))
            .order_by(desc(Transfer.created_at))
        )
    ).scalars().all()

    if not transfers:
        return []

    recipient_ids = list({transfer.recipient_id for transfer in transfers})
    recipients = (
        await db.execute(select(User).where(User.id.in_(recipient_ids)))
    ).scalars().all()
    recipient_map = {user.id: user for user in recipients}

    grouped: dict[int, dict] = {}
    for transfer in transfers:
        amount_display = await convert_amount(
            db,
            transfer.amount,
            transfer.currency,
            display_currency,
        )
        remaining_display = await convert_amount(
            db,
            transfer.remaining_amount,
            transfer.currency,
            display_currency,
        )
        spent_display = amount_display - remaining_display

        if transfer.recipient_id not in grouped:
            recipient = recipient_map.get(transfer.recipient_id)
            grouped[transfer.recipient_id] = {
                'recipient_id': transfer.recipient_id,
                'recipient_username': recipient.username if recipient else None,
                'recipient_name': _display_user_ref(recipient) if recipient else str(transfer.recipient_id),
                'transfer_count': 0,
                'amount': Decimal('0'),
                'remaining_amount': Decimal('0'),
                'spent_amount': Decimal('0'),
                'currency': display_currency,
                'last_transfer_at': transfer.created_at,
            }

        group = grouped[transfer.recipient_id]
        group['transfer_count'] += 1
        group['amount'] += amount_display
        group['remaining_amount'] += remaining_display
        group['spent_amount'] += spent_display
        if transfer.created_at > group['last_transfer_at']:
            group['last_transfer_at'] = transfer.created_at

    rows = sorted(grouped.values(), key=lambda item: item['last_transfer_at'], reverse=True)
    page = rows[offset : offset + limit]
    return [
        {
            **item,
            'amount': float(item['amount']),
            'remaining_amount': float(item['remaining_amount']),
            'spent_amount': float(item['spent_amount']),
        }
        for item in page
    ]


@router.get('/sent/grouped/{recipient_id}', response_model=TransferGroupDetailResponse)
async def get_sent_transfer_group_details(
    recipient_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    display_currency = normalize_currency(current_user.default_currency, 'UZS')

    transfers = (
        await db.execute(
            select(Transfer)
            .where(
                Transfer.group_id == await get_active_group_id(db, current_user),
                Transfer.sender_id == current_user.id,
                Transfer.recipient_id == recipient_id,
            )
            .order_by(desc(Transfer.created_at))
        )
    ).scalars().all()

    if not transfers:
        raise HTTPException(
            status_code=404,
            detail=_t(
                lang,
                "Ushbu foydalanuvchiga o'tkazmalar topilmadi",
                'Переводы этому пользователю не найдены',
                'No transfers found for this recipient',
            ),
        )

    recipient = (await db.execute(select(User).where(User.id == recipient_id))).scalar_one_or_none()
    recipient_name = _display_user_ref(recipient) if recipient else str(recipient_id)
    recipient_username = recipient.username if recipient else None

    transfer_ids = [transfer.id for transfer in transfers]
    transfer_map = {transfer.id: transfer for transfer in transfers}

    total_amount = Decimal('0')
    total_remaining = Decimal('0')
    transfer_items: list[dict] = []

    for transfer in transfers:
        amount_display = await convert_amount(
            db, transfer.amount, transfer.currency, display_currency
        )
        remaining_display = await convert_amount(
            db, transfer.remaining_amount, transfer.currency, display_currency
        )
        spent_display = amount_display - remaining_display

        total_amount += amount_display
        total_remaining += remaining_display
        transfer_items.append(
            {
                'id': transfer.id,
                'amount': float(amount_display),
                'remaining_amount': float(remaining_display),
                'spent_amount': float(spent_display),
                'currency': display_currency,
                'status': transfer.status.value if hasattr(transfer.status, 'value') else str(transfer.status),
                'description': transfer.description,
                'created_at': transfer.created_at,
            }
        )

    expense_rows = (
        await db.execute(
            select(TransferExpense)
            .where(TransferExpense.transfer_id.in_(transfer_ids))
            .order_by(desc(TransferExpense.created_at))
        )
    ).scalars().all()

    category_ids = list({expense.category_id for expense in expense_rows if expense.category_id})
    category_map: dict[int, Category] = {}
    if category_ids:
        categories = (
            await db.execute(select(Category).where(Category.id.in_(category_ids)))
        ).scalars().all()
        category_map = {category.id: category for category in categories}

    grouped_expenses: list[dict] = []
    for expense in expense_rows:
        transfer = transfer_map.get(expense.transfer_id)
        if not transfer:
            continue

        category = category_map.get(expense.category_id) if expense.category_id else None
        amount_display = await convert_amount(
            db,
            expense.amount,
            transfer.currency,
            display_currency,
        )

        grouped_expenses.append(
            {
                'id': str(expense.id),
                'transfer_id': str(expense.transfer_id),
                'amount': float(amount_display),
                'currency': display_currency,
                'category': {
                    'id': category.id if category else None,
                    'name': category.name if category else _t(lang, "Noma'lum", 'Неизвестно', 'Unknown'),
                    'icon': category.icon if category else '💰',
                },
                'description': expense.description,
                'created_at': expense.created_at,
            }
        )

    total_spent = total_amount - total_remaining
    return {
        'recipient_id': recipient_id,
        'recipient_username': recipient_username,
        'recipient_name': recipient_name,
        'transfer_count': len(transfers),
        'amount': float(total_amount),
        'remaining_amount': float(total_remaining),
        'spent_amount': float(total_spent),
        'currency': display_currency,
        'last_transfer_at': transfers[0].created_at,
        'transfers': transfer_items,
        'expenses': grouped_expenses,
    }


@router.get('/received', response_model=list[TransferResponse])
async def get_received_transfers(
    limit: int = Query(20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transfers = (
        await db.execute(
            select(Transfer)
            .where(Transfer.recipient_id == current_user.id)
            .where(Transfer.group_id == await get_active_group_id(db, current_user))
            .order_by(desc(Transfer.created_at))
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    response = []
    for transfer in transfers:
        sender = (
            await db.execute(select(User).where(User.id == transfer.sender_id))
        ).scalar_one_or_none()
        response.append(
            await _serialize_transfer_for_user(
                db,
                transfer,
                current_user,
                with_expenses=False,
                counterpart_user=sender,
            )
        )

    return response


@router.get('/recipients', response_model=list[TransferRecipientResponse])
async def get_transfer_recipients(
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_group = await get_active_group_id(db, current_user)
    query = (
        select(User)
        .join(UserGroup, UserGroup.user_id == User.id)
        .where(
        User.is_active.is_(True),
        User.id != current_user.id,
        UserGroup.group_id == current_group,
    ))

    if search:
        term = search.strip()
        if term:
            pattern = f"%{term}%"
            search_conditions = [
                User.username.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
            ]
            if term.isdigit():
                search_conditions.append(User.id == int(term))
            query = query.where(or_(*search_conditions))

    users = (
        await db.execute(
            query.order_by(desc(User.updated_at), desc(User.created_at)).limit(limit)
        )
    ).scalars().all()

    # Fallback to global active users if group is empty and no search provided
    if not users and not search:
        users = (
            await db.execute(
                select(User)
                .where(
                    User.is_active.is_(True),
                    User.id != current_user.id,
                )
                .order_by(desc(User.updated_at), desc(User.created_at))
                .limit(limit)
            )
        ).scalars().all()

    payload: list[dict] = []
    for user in users:
        if user.username:
            display_name = f"@{user.username}"
        else:
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            display_name = full_name or str(user.id)

        payload.append(
            {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'display_name': display_name,
            }
        )

    return payload


@router.post('/', response_model=TransferResponse)
async def create_transfer(
    transfer_data: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    current_group = await get_active_group_id(db, current_user)
    recipient = await _resolve_recipient(db, current_user, transfer_data, lang)

    if recipient.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail=_t(lang, "O'zingizga o'tkazma qilib bo'lmaydi", 'Нельзя переводить себе', 'Cannot transfer to yourself'),
        )
    recipient_has_access = (
        await db.execute(
            select(UserGroup).where(UserGroup.user_id == recipient.id, UserGroup.group_id == current_group)
        )
    ).scalar_one_or_none()
    if not recipient_has_access:
        raise HTTPException(
            status_code=403,
            detail=_t(
                lang,
                "Qabul qiluvchi sizning guruhingizda emas",
                'Получатель не состоит в вашей группе',
                'Recipient is not in your group',
            ),
        )

    currency = normalize_currency(transfer_data.currency, current_user.default_currency)
    amount = Decimal(str(transfer_data.amount))

    balance = await get_user_balance_summary(db, current_user, currency, group_id=current_group)
    if amount > balance['own_balance']:
        raise HTTPException(
            status_code=400,
            detail=_t(
                lang,
                f"Mablag' yetarli emas. Mavjud: {balance['own_balance']} {currency}",
                f"Недостаточно средств. Доступно: {balance['own_balance']} {currency}",
                f"Insufficient own balance. Available: {balance['own_balance']} {currency}",
            ),
        )

    transfer = Transfer(
        group_id=current_group,
        sender_id=current_user.id,
        recipient_id=recipient.id,
        amount=amount,
        remaining_amount=amount,
        currency=currency,
        status=TransferStatus.COMPLETED,
        description=transfer_data.description,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(transfer)
    await db.flush()

    sender_lang = _lang(current_user.language_code)
    recipient_lang = _lang(recipient.language_code)
    sender_target = _display_user_ref(recipient)
    recipient_source = _display_user_ref(current_user)

    db.add(
        Transaction(
            user_id=current_user.id,
            group_id=current_group,
            type=TransactionType.TRANSFER_OUT,
            amount=amount,
            currency=currency,
            description=_t(
                sender_lang,
                f"{sender_target} ga o'tkazma",
                f"Перевод {sender_target}",
                f"Transfer to {sender_target}",
            ),
            transfer_id=transfer.id,
        )
    )

    db.add(
        Transaction(
            user_id=recipient.id,
            group_id=current_group,
            type=TransactionType.TRANSFER_IN,
            amount=amount,
            currency=currency,
            description=_t(
                recipient_lang,
                f"{recipient_source} dan o'tkazma",
                f"Перевод от {recipient_source}",
                f"Transfer from {recipient_source}",
            ),
            transfer_id=transfer.id,
        )
    )

    await db.commit()
    await db.refresh(transfer)

    await notify_transfer_participants(
        sender=current_user,
        recipient=recipient,
        transfer=transfer,
        bot=None,
    )

    return await _serialize_transfer_for_user(
        db,
        transfer,
        current_user,
        with_expenses=False,
        counterpart_user=recipient,
    )


@router.get('/{transfer_id}', response_model=TransferResponse)
async def get_transfer_details(
    transfer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transfer = (
        await db.execute(
            select(Transfer).where(
                and_(
                    Transfer.id == transfer_id,
                    Transfer.group_id == await get_active_group_id(db, current_user),
                    or_(
                        Transfer.sender_id == current_user.id,
                        Transfer.recipient_id == current_user.id,
                    ),
                )
            )
        )
    ).scalar_one_or_none()

    if not transfer:
        lang = _lang(current_user.language_code)
        raise HTTPException(
            status_code=404,
            detail=_t(lang, "O'tkazma topilmadi", 'Перевод не найден', 'Transfer not found'),
        )

    other_user_id = transfer.recipient_id if transfer.sender_id == current_user.id else transfer.sender_id
    other_user = (
        await db.execute(select(User).where(User.id == other_user_id))
    ).scalar_one_or_none()

    return await _serialize_transfer_for_user(
        db,
        transfer,
        current_user,
        with_expenses=True,
        counterpart_user=other_user,
    )
