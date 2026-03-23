from decimal import Decimal
from types import SimpleNamespace

import pytest

from api.routers import statistics as statistics_router
from database.models import TransactionType


class _FakeScalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _FakeResult:
    def __init__(self, rows=None, scalars=None):
        self._rows = rows or []
        self._scalars = scalars or []

    def all(self):
        return self._rows

    def scalars(self):
        return _FakeScalars(self._scalars)


class _FakeDB:
    def __init__(self, responses):
        self._responses = responses
        self._idx = 0

    async def execute(self, _query):
        if self._idx >= len(self._responses):
            raise AssertionError('Unexpected extra DB execute call')
        response = self._responses[self._idx]
        self._idx += 1
        return response


@pytest.mark.asyncio
async def test_get_statistics_calculates_totals_and_top_categories(monkeypatch):
    async def fake_convert_amount(_db, amount, _from_currency, _to_currency):
        return Decimal(str(amount))

    async def fake_active_group_id(_db, _user):
        return 10

    monkeypatch.setattr(statistics_router, 'convert_amount', fake_convert_amount)
    monkeypatch.setattr(statistics_router, 'get_active_group_id', fake_active_group_id)

    tx_rows = [
        (TransactionType.INCOME, Decimal('100.00'), 'USD', None),
        (TransactionType.EXPENSE, Decimal('50.00'), 'USD', 1),
        (TransactionType.TRANSFER_OUT, Decimal('10.00'), 'USD', None),
        (TransactionType.INCOME, Decimal('20.00'), 'USD', None),
    ]
    category = SimpleNamespace(id=1, name='Food', icon='🍔')

    db = _FakeDB(
        responses=[
            _FakeResult(rows=tx_rows),
            _FakeResult(scalars=[category]),
        ]
    )
    current_user = SimpleNamespace(id=1, default_currency='USD', language_code='en')

    result = await statistics_router.get_statistics(
        period='month',
        current_user=current_user,
        db=db,
    )

    assert result['total_income'] == 120.0
    assert result['total_expense'] == 60.0
    assert result['difference'] == 60.0
    assert len(result['top_categories']) == 1
    assert result['top_categories'][0]['name'] == 'Food'
    assert result['top_categories'][0]['amount'] == 50.0
    assert result['top_categories'][0]['percent'] == 83.3
