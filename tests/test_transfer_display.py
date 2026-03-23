from types import SimpleNamespace

from bot.services.notifications import _user_display_name


def test_user_display_name_prefers_username():
    user = SimpleNamespace(username='john_doe', first_name='John', last_name='Doe', id=11)
    assert _user_display_name(user) == '@john_doe'


def test_user_display_name_falls_back_to_full_name():
    user = SimpleNamespace(username=None, first_name='John', last_name='Doe', id=11)
    assert _user_display_name(user) == 'John Doe'


def test_user_display_name_falls_back_to_id():
    user = SimpleNamespace(username=None, first_name='', last_name='', id=11)
    assert _user_display_name(user) == '11'
