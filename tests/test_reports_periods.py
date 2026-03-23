from bot.handlers.reports import _resolve_period_from_token
from bot.keyboards import get_report_period_keyboard


def test_report_period_token_mapping():
    assert _resolve_period_from_token('daily') == 'day'
    assert _resolve_period_from_token('weekly') == 'week'
    assert _resolve_period_from_token('monthly') == 'month'
    assert _resolve_period_from_token('yearly') == 'year'
    assert _resolve_period_from_token('day') == 'day'
    assert _resolve_period_from_token('week') == 'week'
    assert _resolve_period_from_token('month') == 'month'
    assert _resolve_period_from_token('year') == 'year'
    assert _resolve_period_from_token('unknown') is None


def test_report_period_keyboard_has_expected_callbacks():
    markup = get_report_period_keyboard('en')
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]

    assert 'report_daily' in callbacks
    assert 'report_weekly' in callbacks
    assert 'report_monthly' in callbacks
    assert 'report_yearly' in callbacks
    assert 'report_custom' not in callbacks
