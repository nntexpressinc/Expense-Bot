from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select, update, cast, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.auth import get_current_user
from config.admin import check_user_admin_status, is_user_admin
from database.finance import convert_amount
from database.models import Category, Transaction, Transfer, TransferExpense, User
from database.session import get_db

router = APIRouter(prefix='/admin', tags=['admin'])


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_transactions: int
    total_transfers: int
    total_volume: float


class UserListItem(BaseModel):
    id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    language_code: str
    default_currency: str
    group_id: Optional[int]
    is_admin: bool
    is_active: bool
    created_at: str


class UpdateUserAdminRequest(BaseModel):
    user_id: int
    is_admin: bool


class TransferUsageExpense(BaseModel):
    amount: float
    currency: str
    category: Optional[str]
    description: Optional[str]
    date: str
    attachment_file_id: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_name: Optional[str] = None


class TransferUsageItem(BaseModel):
    transfer_id: str
    sender_id: int
    sender_username: Optional[str]
    recipient_id: int
    recipient_username: Optional[str]
    amount: float
    remaining_amount: float
    currency: str
    spent_amount: float
    spent_percent: float
    created_at: str
    expenses: List[TransferUsageExpense]


class GroupSummary(BaseModel):
    group_id: int
    members: int
    admins: int


class UpdateUserGroupRequest(BaseModel):
    group_id: int


def _effective_group_id(user: User) -> int:
    return int(user.group_id or user.id)


async def verify_admin(current_user: User) -> tuple[bool, int]:
    if not await check_user_admin_status(current_user):
        raise HTTPException(status_code=403, detail='Admin access required')
    return is_user_admin(current_user.id), _effective_group_id(current_user)


@router.get('/groups', response_model=List[GroupSummary])
async def list_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_super_admin, admin_group = await verify_admin(current_user)

    query = (
        select(
            User.group_id.label('group_id'),
            func.count(User.id).label('members'),
            func.coalesce(func.sum(cast(User.is_admin, Integer)), 0).label('admins'),
        )
        .group_by(User.group_id)
        .order_by(User.group_id)
    )
    if not is_super_admin:
        query = query.where(User.group_id == admin_group)

    rows = (await db.execute(query)).all()
    return [
        {
            'group_id': int(row.group_id),
            'members': int(row.members or 0),
            'admins': int(row.admins or 0),
        }
        for row in rows
    ]


@router.get('/stats', response_model=AdminStatsResponse)
async def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_super_admin, admin_group = await verify_admin(current_user)

    group_user_ids = select(User.id).where(User.group_id == admin_group)
    if is_super_admin:
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        active_users = (
            await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))
        ).scalar() or 0
        total_transactions = (await db.execute(select(func.count(Transaction.id)))).scalar() or 0
        total_transfers = (await db.execute(select(func.count(Transfer.id)))).scalar() or 0
        tx_rows = (await db.execute(select(Transaction.amount, Transaction.currency))).all()
    else:
        total_users = (
            await db.execute(select(func.count(User.id)).where(User.group_id == admin_group))
        ).scalar() or 0
        active_users = (
            await db.execute(
                select(func.count(User.id)).where(
                    User.group_id == admin_group,
                    User.is_active.is_(True),
                )
            )
        ).scalar() or 0
        total_transactions = (
            await db.execute(
                select(func.count(Transaction.id)).where(Transaction.user_id.in_(group_user_ids))
            )
        ).scalar() or 0
        total_transfers = (
            await db.execute(
                select(func.count(Transfer.id)).where(Transfer.sender_id.in_(group_user_ids))
            )
        ).scalar() or 0
        tx_rows = (
            await db.execute(
                select(Transaction.amount, Transaction.currency).where(
                    Transaction.user_id.in_(group_user_ids)
                )
            )
        ).all()

    total_volume = Decimal('0')
    for amount, currency in tx_rows:
        total_volume += await convert_amount(db, amount, currency, 'UZS')

    return {
        'total_users': total_users,
        'active_users': active_users,
        'total_transactions': total_transactions,
        'total_transfers': total_transfers,
        'total_volume': float(total_volume),
    }


@router.get('/users', response_model=List[UserListItem])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_super_admin, admin_group = await verify_admin(current_user)

    query = select(User)
    if not is_super_admin:
        query = query.where(User.group_id == admin_group)
    if search:
        search_pattern = f'%{search}%'
        query = query.where(
            or_(
                User.username.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
            )
        )

    users = (
        await db.execute(query.order_by(User.created_at.desc()).offset(skip).limit(limit))
    ).scalars().all()

    return [
        {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'language_code': user.language_code,
            'default_currency': user.default_currency,
            'group_id': _effective_group_id(user),
            'is_admin': await check_user_admin_status(user),
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat(),
        }
        for user in users
    ]


@router.get('/users/{user_id}')
async def get_user_details(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_super_admin, admin_group = await verify_admin(current_user)

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or (not is_super_admin and _effective_group_id(user) != admin_group):
        raise HTTPException(status_code=404, detail='User not found')

    transactions_count = (
        await db.execute(select(func.count(Transaction.id)).where(Transaction.user_id == user_id))
    ).scalar() or 0
    transfers_sent = (
        await db.execute(select(func.count(Transfer.id)).where(Transfer.sender_id == user_id))
    ).scalar() or 0
    transfers_received = (
        await db.execute(select(func.count(Transfer.id)).where(Transfer.recipient_id == user_id))
    ).scalar() or 0

    return {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code,
        'default_currency': user.default_currency,
        'group_id': _effective_group_id(user),
        'is_admin': await check_user_admin_status(user),
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat(),
        'updated_at': user.updated_at.isoformat(),
        'stats': {
            'transactions_count': transactions_count,
            'transfers_sent': transfers_sent,
            'transfers_received': transfers_received,
        },
    }


@router.get('/transfers/usage', response_model=List[TransferUsageItem])
async def get_transfer_usage(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_super_admin, admin_group = await verify_admin(current_user)

    query = select(Transfer)
    if not is_super_admin:
        group_user_ids = select(User.id).where(User.group_id == admin_group)
        query = query.where(Transfer.sender_id.in_(group_user_ids))
    transfers = (await db.execute(query.order_by(Transfer.created_at.desc()).limit(limit).offset(offset))).scalars().all()

    payload: List[TransferUsageItem] = []
    for transfer in transfers:
        sender = (await db.execute(select(User).where(User.id == transfer.sender_id))).scalar_one_or_none()
        recipient = (await db.execute(select(User).where(User.id == transfer.recipient_id))).scalar_one_or_none()

        expenses = (
            await db.execute(
                select(TransferExpense).where(TransferExpense.transfer_id == transfer.id)
            )
        ).scalars().all()

        expense_rows: List[TransferUsageExpense] = []
        spent = Decimal('0')

        for expense in expenses:
            spent += Decimal(str(expense.amount))
            category_name = None
            transaction = (
                await db.execute(select(Transaction).where(Transaction.id == expense.transaction_id))
            ).scalar_one_or_none()
            if expense.category_id:
                cat = (await db.execute(select(Category).where(Category.id == expense.category_id))).scalar_one_or_none()
                category_name = cat.name if cat else None

            expense_rows.append(
                {
                    'amount': float(expense.amount),
                    'currency': transfer.currency,
                    'category': category_name,
                    'description': expense.description,
                    'date': expense.created_at.isoformat(),
                    'attachment_file_id': transaction.attachment_file_id if transaction else None,
                    'attachment_type': transaction.attachment_type if transaction else None,
                    'attachment_name': transaction.attachment_name if transaction else None,
                }
            )

        amount = Decimal(str(transfer.amount))
        remaining = Decimal(str(transfer.remaining_amount))
        spent_amount = amount - remaining
        spent_percent = float((spent_amount / amount * 100) if amount > 0 else Decimal('0'))

        payload.append(
            {
                'transfer_id': str(transfer.id),
                'sender_id': transfer.sender_id,
                'sender_username': sender.username if sender else None,
                'recipient_id': transfer.recipient_id,
                'recipient_username': recipient.username if recipient else None,
                'amount': float(amount),
                'remaining_amount': float(remaining),
                'currency': transfer.currency,
                'spent_amount': float(spent_amount),
                'spent_percent': round(spent_percent, 2),
                'created_at': transfer.created_at.isoformat(),
                'expenses': expense_rows,
            }
        )

    return payload


@router.patch('/users/{user_id}/admin')
async def update_user_admin_status(
    user_id: int,
    request: UpdateUserAdminRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_super_admin, admin_group = await verify_admin(current_user)

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or (not is_super_admin and _effective_group_id(user) != admin_group):
        raise HTTPException(status_code=404, detail='User not found')

    if user_id == current_user.id and not request.is_admin:
        raise HTTPException(status_code=400, detail='Cannot remove admin status from yourself')

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_admin=request.is_admin)
    )
    await db.commit()

    return {'success': True, 'user_id': user_id, 'is_admin': request.is_admin}


@router.patch('/users/{user_id}/activate')
async def toggle_user_active_status(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_super_admin, admin_group = await verify_admin(current_user)

    if user_id == current_user.id and not is_active:
        raise HTTPException(status_code=400, detail='Cannot deactivate yourself')
    target_user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target_user or (not is_super_admin and _effective_group_id(target_user) != admin_group):
        raise HTTPException(status_code=404, detail='User not found')

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=is_active)
    )
    await db.commit()

    return {'success': True, 'user_id': user_id, 'is_active': is_active}


@router.patch('/users/{user_id}/group')
async def update_user_group(
    user_id: int,
    request: UpdateUserGroupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_super_admin, admin_group = await verify_admin(current_user)

    target_user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail='User not found')

    # Non-super admins can only move users into their own group and manage users from their group
    if not is_super_admin:
        if request.group_id != admin_group:
            raise HTTPException(status_code=403, detail='You can only move users to your group')
        if _effective_group_id(target_user) != admin_group:
            raise HTTPException(status_code=404, detail='User not found')

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(group_id=request.group_id)
    )
    await db.commit()

    return {'success': True, 'user_id': user_id, 'group_id': request.group_id}


@router.delete('/users/{user_id}')
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_super_admin, admin_group = await verify_admin(current_user)

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail='Cannot delete yourself')

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or (not is_super_admin and _effective_group_id(user) != admin_group):
        raise HTTPException(status_code=404, detail='User not found')

    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()

    return {'success': True, 'message': f'User {user_id} deleted'}
