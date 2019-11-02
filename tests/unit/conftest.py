#!/usr/bin/python3
"""Test fixtures for unit testing."""
import mock
import pytest

from charmhelpers.core import unitdata


@pytest.fixture
def mock_snap(monkeypatch):
    """Mock snap layer."""
    monkeypatch.syspath_prepend(".")
    monkeypatch.setattr("charms.layer.snap", mock.Mock())


@pytest.fixture
def mock_host_service(monkeypatch):
    """Mock host import on lib_matrix."""
    def mocked_service(action, name):
        print("Called {} on {}".format(
            action,
            name
        ))
        return True

    mock_service = mock.Mock()
    mock_service.side_effect = mocked_service
    monkeypatch.setattr("lib_matrix.host.service", mock_service)
    return mock_service


@pytest.fixture
def mock_lsb_release(monkeypatch):
    """Mock lsb_release function charmhelpers."""
    def mocked_lsb_release():
        return {
            'DISTRIB_CODENAME': 'xenial'
        }

    mock_lsb = mock.Mock()
    mock_lsb.side_effect = mocked_lsb_release
    monkeypatch.setattr("lib_matrix.host.lsb_release", mock_lsb)
    return mock_lsb


@pytest.fixture
def mock_psycopg2(monkeypatch):
    """Mock useful psycopg2 calls."""
    mock_execute = mock.Mock()
    mock_module = mock.Mock()
    mock_connect = mock.Mock()

    def mocked_execute(self, query, vars=None):
        print(query)
        return True

    class Cursor():
        def execute(self, query, vals=None):
            return True

    class Connection:
        def cursor(self):
            return Cursor()

    def mocked_connect():
        return Connection()

    mock_connect.side_effect = mocked_connect
    mock_execute.side_effect = mocked_execute
    monkeypatch.setattr("lib_matrix.psycopg2", mock_module)
    monkeypatch.setattr("lib_matrix.psycopg2.connect", mock_connect)
    monkeypatch.setattr("lib_matrix.psycopg2.Cursor", Cursor())
    monkeypatch.setattr("lib_matrix.psycopg2.Cursor.execute", mock_execute)

    return mock_module


@pytest.fixture
def mock_check_output(monkeypatch):
    """Mock subprocess check_output on lib_matrix."""
    def mocked_check_output(command):
        return 'mocked-output'

    mock_call = mock.Mock()
    mock_call.side_effect = mocked_check_output
    monkeypatch.setattr("lib_matrix.check_output", mock_call)
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
    mock_lsb_release,
    mock_host_service,
    mock_template,
    mock_socket,
    mock_snap,
    monkeypatch,
):
    """Mock the Matrix helper library."""
    from lib_matrix import MatrixHelper

    helper = MatrixHelper()

    # Example config file patching
    homeserver_file = tmpdir.join("homeserver.yaml")
    helper.homeserver_config = homeserver_file.strpath
    synapse_signing_key_file = tmpdir.join("signing.key")
    helper.synapse_signing_key_file = synapse_signing_key_file.strpath

    # Any other functions that load helper will get this version
    monkeypatch.setattr("lib_matrix.MatrixHelper", lambda: helper)

    return helper
