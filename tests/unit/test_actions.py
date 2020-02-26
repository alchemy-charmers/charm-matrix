"""Unit tests for the Matrix charm."""
import imp
import mock


def test_set_password_action(matrix, mock_action_get, mock_action_set, mock_action_fail, mock_juju_unit, monkeypatch):
    """Test setting of passwords via the action."""
    mock_function = mock.Mock()
    monkeypatch.setattr(matrix, "set_password", mock_function)
    assert mock_function.call_count == 0
    imp.load_source("set_password", "./actions/set-password")
    assert mock_function.call_count == 1


def test_register_user_action(matrix, mock_action_get, mock_action_set, mock_action_fail, mock_juju_unit, monkeypatch):
    """Test registration code."""
    mock_function = mock.Mock()
    monkeypatch.setattr(matrix, "register_user", mock_function)
    assert mock_function.call_count == 0
    imp.load_source("register_user", "./actions/register-user")
    assert mock_function.call_count == 1
