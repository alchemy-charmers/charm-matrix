#!/usr/bin/python3
"""Test fixtures for unit testing."""
import mock
import pytest

from charmhelpers.core import unitdata


@pytest.fixture
def mock_layers(monkeypatch):
    """Mock layer configuration."""
    import sys

    sys.modules["charms.layer"] = mock.Mock()
    sys.modules["reactive"] = mock.Mock()
    # Mock any functions in layers that need to be mocked here

    def options(layer):
        # mock options for layers here
        if layer == "example-layer":
            options = {"port": 9999}
            return options
        else:
            return None

    monkeypatch.setattr("lib_matrix.options", options)
    monkeypatch.setattr("lib_matrix.snap", mock.Mock())
    monkeypatch.setattr("charms.layer", mock.Mock())
    monkeypatch.setattr("charms.layer.snap", mock.Mock())


@pytest.fixture
def mock_host_service(monkeypatch):
    """Mock host import on lib_matrix."""
    mock_service = mock.Mock()
    monkeypatch.setattr("lib_matrix.host.service", mock_service)
    return mock_service


@pytest.fixture
def mock_check_call(monkeypatch):
    """Mock subprocess check_call on lib_matrix."""
    mock_call = mock.Mock()
    monkeypatch.setattr("lib_matrix.check_call", mock_call)
    return mock_call


@pytest.fixture
def mock_action_get(monkeypatch):
    """Mock the action_get function."""
    def mock_action_get(name):
        return "blah"

    monkeypatch.setattr("charmhelpers.core.hookenv.action_get", mock_action_get)
    return mock_action_get


@pytest.fixture
def mock_action_set(monkeypatch):
    """Mock the action_set function."""
    mock_action_set = mock.Mock()
    monkeypatch.setattr("charmhelpers.core.hookenv.action_set", mock_action_set)
    return mock_action_set


@pytest.fixture
def mock_action_fail(monkeypatch):
    """Mock the action_fail function."""
    mock_action_fail = mock.Mock()
    monkeypatch.setattr("charmhelpers.core.hookenv.action_fail", mock_action_fail)
    return mock_action_fail


@pytest.fixture
def mock_juju_unit(monkeypatch):
    """Mock calls to retrieve the local unit information."""
    def mock_local_unit():
        return "mocked"

    monkeypatch.setattr("charmhelpers.core.hookenv.local_unit", mock_local_unit)
    return mock_local_unit


@pytest.fixture
def mock_hookenv_config(monkeypatch):
    """Mock the hookenv config helper."""
    import yaml

    def mock_config():
        cfg = {}
        yml = yaml.safe_load(open("./config.yaml"))

        # Load all defaults
        for key, value in yml["options"].items():
            cfg[key] = value["default"]

        # Manually add cfg from other layers
        # cfg['my-other-layer'] = 'mock'
        return cfg

    monkeypatch.setattr("lib_matrix.hookenv.config", mock_config)


@pytest.fixture
def mock_unit_db(monkeypatch):
    """Mock the key value store."""
    mock_kv = mock.Mock()
    mock_kv.return_value = unitdata.Storage(path=":memory:")
    monkeypatch.setattr("libgitlab.unitdata.kv", mock_kv)


@pytest.fixture
def mock_remote_unit(monkeypatch):
    """Mock the relation remote unit."""
    monkeypatch.setattr("lib_matrix.hookenv.remote_unit", lambda: "unit-mock/0")


@pytest.fixture
def mock_charm_dir(monkeypatch):
    """Mock the charm dir path."""
    monkeypatch.setattr("lib_matrix.hookenv.charm_dir", lambda: ".")


@pytest.fixture
def mock_template(monkeypatch):
    """Mock syscalls used in the tempating library to prevent permissions problems."""
    monkeypatch.setattr("lib_matrix.templating.host.os.fchown", mock.Mock())
    monkeypatch.setattr("lib_matrix.templating.host.os.chown", mock.Mock())
    monkeypatch.setattr("lib_matrix.templating.host.os.fchmod", mock.Mock())


@pytest.fixture
def mock_socket(monkeypatch):
    """Mock common socket library functions for testing with known inputs."""
    monkeypatch.setattr("lib_matrix.socket.getfqdn", lambda: "mockhost")


@pytest.fixture
def matrix(
    tmpdir,
    mock_hookenv_config,
    mock_charm_dir,
    mock_template,
    mock_socket,
    mock_layers,
    monkeypatch,
):
    """Mock the Matrix helper library."""
    from lib_matrix import MatrixHelper

    helper = MatrixHelper()

    # Example config file patching
    homeserver_file = tmpdir.join("homeserver.yaml")
    helper.homeserver_config = homeserver_file.strpath

    # Any other functions that load helper will get this version
    monkeypatch.setattr("lib_matrix.MatrixHelper", lambda: helper)

    return helper
