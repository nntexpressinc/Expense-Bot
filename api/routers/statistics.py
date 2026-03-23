from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.auth import get_current_user
from database.finance import convert_amount, normalize_currency
from database.group_context import get_active_group_id
from database.models import Category, Transaction, TransactionType, User
from database.reporting import generate_excel_report
from database.session import get_db

router = APIRouter()


class CategoryStat(BaseModel):
    id: int
    name: str
    icon: str
    amount: float
    percent: float


class StatisticsResponse(BaseModel):
    period: str
    total_income: float
    total_expense: float
    difference: float
    top_categories: List[CategoryStat]


def _period_start(period: str) -> tuple[datetime, str]:
    now = datetime.now()
    if period == 'day':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, 'day'
    if period == 'week':
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, 'week'
    if period == 'year':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, 'year'
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, 'month'


def _period_label(lang: str, label_type: str, start: datetime, now: datetime) -> str:
    if label_type == 'day':
        return {
            'uz': f"Bugun ({start.strftime('%d.%m.%Y')})",
            'ru': f"\u0421\u0435\u0433\u043e\u0434\u043d\u044f ({start.strftime('%d.%m.%Y')})",
            'en': f"Today ({start.strftime('%d.%m.%Y')})",
        }.get(lang, f"Bugun ({start.strftime('%d.%m.%Y')})")
    if label_type == 'week':
        return {
            'uz': f"Hafta ({start.strftime('%d.%m')} - {now.strftime('%d.%m.%Y')})",
            'ru': f"\u041d\u0435\u0434\u0435\u043b\u044f ({start.strftime('%d.%m')} - {now.strftime('%d.%m.%Y')})",
            'en': f"Week ({start.strftime('%d.%m')} - {now.strftime('%d.%m.%Y')})",
        }.get(lang, f"Hafta ({start.strftime('%d.%m')} - {now.strftime('%d.%m.%Y')})")
    if label_type == 'year':
        return {'uz': f"{start.year} yil", 'ru': f"{start.year} \u0433\u043e\u0434", 'en': f"{start.year}"}.get(lang, f"{start.year} yil")
    month_name = start.strftime('%B %Y')
    return {'uz': month_name, 'ru': month_name, 'en': month_name}.get(lang, month_name)


@router.get('/export/excel')
async def export_statistics_excel(
    period: str = Query('month', pattern='^(day|week|month|year)$'),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content, filename = await generate_excel_report(db, current_user, period, filename_prefix='statistics')
    return StreamingResponse(
        BytesIO(content),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.get('/', response_model=StatisticsResponse)
async def get_statistics(
    period: str = Query('month', pattern='^(day|week|month|year)$'),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now()
    start_date, label_type = _period_start(period)
    currency = normalize_currency(current_user.default_currency, 'UZS')
    lang = (current_user.language_code or 'uz').split('-')[0].lower()
    group_id = await get_active_group_id(db, current_user)

    rows = (
        await db.execute(
            select(Transaction.type, Transaction.debt_kind, Transaction.amount, Transaction.currency, Transaction.category_id)
            .where(
                and_(
                    Transaction.user_id == current_user.id,
                    Transaction.group_id == group_id,
                    Transaction.transaction_date >= start_date,
                )
            )
        )
    ).all()

    total_income = Decimal('0')
    total_expense = Decimal('0')
    category_totals: dict[int, Decimal] = {}

    for row in rows:
        if len(row) >= 5:
            tx_type, debt_kind, amount, tx_currency, category_id = row
        else:
            tx_type, amount, tx_currency, category_id = row
            debt_kind = None
        tx_type_val = tx_type.value if hasattr(tx_type, 'value') else str(tx_type)
        converted = await convert_amount(db, amount, tx_currency, currency)

        if tx_type_val == TransactionType.INCOME.value:
            total_income += converted
        elif tx_type_val == TransactionType.DEBT.value and debt_kind == 'credit_purchase':
            total_expense += converted
        elif tx_type_val in {
            TransactionType.EXPENSE.value,
            TransactionType.TRANSFER_OUT.value,
            TransactionType.DEBT_PAYMENT.value,
        }:
            total_expense += converted
            if tx_type_val == TransactionType.EXPENSE.value and category_id:
                category_totals[category_id] = category_totals.get(category_id, Decimal('0')) + converted

    top_categories: List[dict] = []
    if category_totals:
        category_ids = list(category_totals.keys())
        categories = (await db.execute(select(Category).where(Category.id.in_(category_ids)))).scalars().all()
        category_map = {cat.id: cat for cat in categories}

        ordered = sorted(category_totals.items(), key=lambda item: item[1], reverse=True)[:5]
        for cat_id, amount_value in ordered:
            cat = category_map.get(cat_id)
            percent = float((amount_value / total_expense * 100) if total_expense > 0 else Decimal('0'))
            top_categories.append(
                {
                    'id': cat_id,
                    'name': cat.name if cat else 'Unknown',
                    'icon': cat.icon if cat else '$',
                    'amount': float(amount_value),
                    'percent': round(percent, 1),
                }
            )

    return {
        'period': _period_label(lang, label_type, start_date, now),
        'total_income': float(total_income),
        'total_expense': float(total_expense),
        'difference': float(total_income - total_expense),
        'top_categories': top_categories,
    }
