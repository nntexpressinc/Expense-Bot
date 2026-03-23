from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.auth import get_current_user
from database.audit import write_audit_log
from database.finance import (
    allocate_expense_to_transfers,
    apply_debt_usage,
    convert_amount,
    get_available_debt_for_entry,
    get_spendable_main_balance,
    normalize_currency,
    normalize_debt_kind,
    normalize_funding_source,
)
from database.group_context import get_active_group_id
from database.models import Category, Debt, DebtUsage, Transaction, TransactionType, User
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


class TransactionCreate(BaseModel):
    type: str = Field(..., pattern='^(income|expense)$')
    amount: float = Field(..., gt=0)
    currency: Optional[str] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    funding_source: Optional[str] = Field('main', pattern='^(main|debt)$')
    debt_id: Optional[UUID] = None
    attachment_file_id: Optional[str] = None
    attachment_type: Optional[str] = Field(None, pattern='^(photo|document)$')
    attachment_name: Optional[str] = None


class TransactionResponse(BaseModel):
    id: UUID
    type: str
    amount: float
    currency: str
    funding_source: str
    debt_kind: Optional[str] = None
    debt_source_name: Optional[str] = None
    debt_used_amount: Optional[float] = None
    main_used_amount: Optional[float] = None
    category: dict
    description: Optional[str]
    attachment_file_id: Optional[str]
    attachment_type: Optional[str]
    attachment_name: Optional[str]
    transaction_date: datetime


async def _resolve_category(
    db: AsyncSession,
    *,
    current_user: User,
    tx_type: TransactionType,
    category_id: Optional[int],
    lang: str,
) -> Optional[Category]:
    if category_id:
        category = (
            await db.execute(
                select(Category).where(
                    Category.id == category_id,
                    (Category.is_system.is_(True)) | (Category.user_id == current_user.id),
                )
            )
        ).scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=404,
                detail=_t(lang, 'Kategoriya topilmadi', 'Категория не найдена', 'Category not found'),
            )
        return category

    return (
        await db.execute(
            select(Category)
            .where(Category.type == tx_type)
            .order_by(Category.is_system.desc(), Category.id.asc())
            .limit(1)
        )
    ).scalars().first()


async def _resolve_funding_meta(db: AsyncSession, transaction: Transaction) -> dict:
    if transaction.type != TransactionType.EXPENSE or transaction.funding_source != 'debt':
        return {'debt_source_name': None, 'debt_used_amount': None, 'main_used_amount': None}

    usage_row = (
        await db.execute(
            select(DebtUsage, Debt)
            .join(Debt, Debt.id == DebtUsage.debt_id)
            .where(DebtUsage.transaction_id == transaction.id)
        )
    ).first()

    if not usage_row:
        return {
            'debt_source_name': None,
            'debt_used_amount': float(transaction.amount),
            'main_used_amount': 0.0,
        }

    usage, debt = usage_row
    debt_used_amount = await convert_amount(db, usage.amount, usage.currency, transaction.currency)
    debt_used_amount = min(debt_used_amount, Decimal(str(transaction.amount)))
    main_used_amount = max(Decimal('0'), Decimal(str(transaction.amount)) - debt_used_amount)
    return {
        'debt_source_name': debt.source_name or debt.description,
        'debt_used_amount': float(debt_used_amount),
        'main_used_amount': float(main_used_amount),
    }


async def _serialize_transaction(db: AsyncSession, transaction: Transaction, lang: str) -> dict:
    category = None
    if transaction.category_id:
        category = (await db.execute(select(Category).where(Category.id == transaction.category_id))).scalar_one_or_none()

    funding_meta = await _resolve_funding_meta(db, transaction)
    return {
        'id': transaction.id,
        'type': transaction.type.value if hasattr(transaction.type, 'value') else str(transaction.type),
        'amount': float(transaction.amount),
        'currency': transaction.currency,
        'funding_source': transaction.funding_source,
        'debt_kind': transaction.debt_kind,
        'debt_source_name': funding_meta['debt_source_name'],
        'debt_used_amount': funding_meta['debt_used_amount'],
        'main_used_amount': funding_meta['main_used_amount'],
        'category': {
            'id': category.id if category else None,
            'name': category.name if category else _t(lang, "Noma'lum", 'Неизвестно', 'Unknown'),
            'icon': category.icon if category else '💰',
        },
        'description': transaction.description,
        'attachment_file_id': transaction.attachment_file_id,
        'attachment_type': transaction.attachment_type,
        'attachment_name': transaction.attachment_name,
        'transaction_date': transaction.transaction_date,
    }


@router.get('/', response_model=list[TransactionResponse])
async def get_transactions(
    type: Optional[str] = Query(None, pattern='^(income|expense|transfer_out|transfer_in|debt|debt_payment)$'),
    limit: int = Query(20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    group_id = await get_active_group_id(db, current_user)
    query = select(Transaction).where(Transaction.user_id == current_user.id, Transaction.group_id == group_id)

    if type:
        query = query.where(Transaction.type == type)

    transactions = (
        await db.execute(query.order_by(desc(Transaction.transaction_date)).limit(limit).offset(offset))
    ).scalars().all()
    return [await _serialize_transaction(db, transaction, lang) for transaction in transactions]


@router.post('/', response_model=TransactionResponse)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    group_id = await get_active_group_id(db, current_user)
    tx_type = TransactionType.INCOME if transaction_data.type == 'income' else TransactionType.EXPENSE
    currency = normalize_currency(transaction_data.currency, current_user.default_currency)
    funding_source = normalize_funding_source(transaction_data.funding_source)
    amount = Decimal(str(transaction_data.amount))

    if tx_type == TransactionType.INCOME:
        funding_source = 'main'

    category = await _resolve_category(
        db,
        current_user=current_user,
        tx_type=tx_type,
        category_id=transaction_data.category_id,
        lang=lang,
    )

    debt_entry = None
    main_component = amount if tx_type == TransactionType.INCOME else Decimal('0.00')
    debt_component = Decimal('0.00')
    persisted_funding_source = funding_source

    if tx_type == TransactionType.EXPENSE:
        spendable_main = await get_spendable_main_balance(db, current_user, currency, group_id)

        if funding_source == 'main':
            if amount > spendable_main:
                raise HTTPException(
                    status_code=400,
                    detail=_t(
                        lang,
                        f"Asosiy balans yetarli emas. Mavjud: {spendable_main} {currency}. Qolgan qismi uchun qarz manbasini tanlang yoki yangi qarz qo'shing.",
                        f'Недостаточно основного баланса. Доступно: {spendable_main} {currency}. Для остатка выберите источник долга или создайте новый долг.',
                        f'Insufficient main balance. Available: {spendable_main} {currency}. Select a debt source or create a new debt for the remainder.',
                    ),
                )
            main_component = amount
        else:
            if not transaction_data.debt_id:
                raise HTTPException(
                    status_code=400,
                    detail=_t(lang, 'Qarz manbasi tanlanmagan', 'Источник долга не выбран', 'Debt source is required'),
                )

            debt_entry = (
                await db.execute(
                    select(Debt).where(
                        Debt.id == transaction_data.debt_id,
                        Debt.user_id == current_user.id,
                        Debt.group_id == group_id,
                    )
                )
            ).scalar_one_or_none()
            if not debt_entry:
                raise HTTPException(
                    status_code=404,
                    detail=_t(lang, 'Qarz topilmadi', 'Долг не найден', 'Debt not found'),
                )
            if normalize_debt_kind(getattr(debt_entry, 'kind', None)) != 'cash_loan':
                raise HTTPException(
                    status_code=400,
                    detail=_t(
                        lang,
                        "Faqat qarz olingan summa xarajat manbasi bo'la oladi",
                        'Только занятые деньги можно использовать как источник расхода',
                        'Only borrowed money can be used as an expense source',
                    ),
                )

            main_component = Decimal('0.00')
            debt_component = amount.quantize(Decimal('0.01'))
            available_debt = await get_available_debt_for_entry(db, debt_entry, currency)
            if debt_component > available_debt:
                raise HTTPException(
                    status_code=400,
                    detail=_t(
                        lang,
                        f"Tanlangan qarz manbasida yetarli summa yo'q. Mavjud: {available_debt} {currency}. Boshqa qarzni tanlang yoki yangi qarz qo'shing.",
                        f'\u0412 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u043e\u043c \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u0435 \u0434\u043e\u043b\u0433\u0430 \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e\u0439 \u0441\u0443\u043c\u043c\u044b. \u0414\u043e\u0441\u0442\u0443\u043f\u043d\u043e: {available_debt} {currency}. \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0434\u0440\u0443\u0433\u043e\u0439 \u0434\u043e\u043b\u0433 \u0438\u043b\u0438 \u0441\u043e\u0437\u0434\u0430\u0439\u0442\u0435 \u043d\u043e\u0432\u044b\u0439.',
                        f'The selected debt source does not have enough balance. Available: {available_debt} {currency}. Choose another debt or create a new one.',
                    ),
                )

    transaction = Transaction(
        user_id=current_user.id,
        group_id=group_id,
        type=tx_type,
        amount=amount,
        currency=currency,
        category_id=category.id if category else None,
        description=transaction_data.description,
        funding_source=persisted_funding_source,
        attachment_file_id=transaction_data.attachment_file_id,
        attachment_type=transaction_data.attachment_type,
        attachment_name=transaction_data.attachment_name,
    )

    db.add(transaction)
    await db.flush()

    if tx_type == TransactionType.EXPENSE and main_component > 0:
        await allocate_expense_to_transfers(
            db=db,
            user_id=current_user.id,
            group_id=group_id,
            transaction_id=transaction.id,
            amount=main_component,
            currency=currency,
            category_id=category.id if category else None,
            description=transaction_data.description,
        )

    if tx_type == TransactionType.EXPENSE and debt_entry and debt_component > 0:
        await apply_debt_usage(
            db,
            debt=debt_entry,
            transaction=transaction,
            amount=debt_component,
            currency=currency,
            note=transaction_data.description,
        )

    await write_audit_log(
        db,
        action='transaction.created',
        entity_type='transaction',
        entity_id=str(transaction.id),
        actor=current_user,
        group_id=group_id,
        payload={
            'type': transaction.type.value,
            'amount': str(amount),
            'currency': currency,
            'funding_source': persisted_funding_source,
            'main_used_amount': str(main_component),
            'debt_used_amount': str(debt_component),
            'debt_id': str(transaction_data.debt_id) if transaction_data.debt_id else None,
        },
    )

    await db.commit()
    await db.refresh(transaction)
    return await _serialize_transaction(db, transaction, lang)


@router.delete('/{transaction_id}')
async def delete_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lang = _lang(current_user.language_code)
    group_id = await get_active_group_id(db, current_user)
    transaction = (
        await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.id == transaction_id,
                    Transaction.user_id == current_user.id,
                    Transaction.group_id == group_id,
                )
            )
        )
    ).scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=_t(lang, 'Operatsiya topilmadi', 'Операция не найдена', 'Transaction not found'),
        )

    if transaction.funding_source == 'debt':
        raise HTTPException(
            status_code=409,
            detail=_t(
                lang,
                "Qarz bilan bog'langan operatsiyani qo'lda o'chirib bo'lmaydi",
                'Операцию, связанную с долгом, нельзя удалить вручную',
                'Debt-linked transaction cannot be deleted manually',
            ),
        )

    await db.delete(transaction)
    await write_audit_log(
        db,
        action='transaction.deleted',
        entity_type='transaction',
        entity_id=str(transaction.id),
        actor=current_user,
        group_id=group_id,
        payload={'type': transaction.type.value},
    )
    await db.commit()

    return {'message': _t(lang, "Operatsiya o'chirildi", 'Операция удалена', 'Transaction deleted successfully')}
