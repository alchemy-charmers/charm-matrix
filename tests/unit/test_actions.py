import imp

import mock


def test_set_password_action(matrix, monkeypatch):
    mock_function = mock.Mock()
    monkeypatch.setattr(matrix, "set_password", mock_function)
    assert mock_function.call_count == 0
    imp.load_source("set_password", "./actions/set-password")
    assert mock_function.call_count == 1


def test_register_user_action(matrix, monkeypatch):
    mock_function = mock.Mock()
    monkeypatch.setattr(matrix, "register_user", mock_function)
    assert mock_function.call_count == 0
    imp.load_source("register_user", "./actions/register-user")
    assert mock_function.call_count == 1
