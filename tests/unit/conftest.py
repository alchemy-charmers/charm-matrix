#!/usr/bin/python3
import mock
import pytest


# If layer options are used, add this to pihole
# and import layer in lib_matrix
@pytest.fixture
def mock_layers(monkeypatch):
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

    monkeypatch.setattr("lib_matrix.layer.options", options)


@pytest.fixture
def mock_action_get(monkeypatch):

    def mock_action_get(name):
        return 'blah'

    monkeypatch.setattr('charmhelpers.core.hookenv.action_get',
                        mock_action_get)
    return mock_action_get


@pytest.fixture
def mock_action_set(monkeypatch):

    mock_action_set = mock.Mock()
    monkeypatch.setattr('charmhelpers.core.hookenv.action_set',
                        mock_action_set)
    return mock_action_set


@pytest.fixture
def mock_action_fail(monkeypatch):

    mock_action_fail = mock.Mock()
    monkeypatch.setattr('charmhelpers.core.hookenv.action_fail',
                        mock_action_fail)
    return mock_action_fail


@pytest.fixture
def mock_juju_unit(monkeypatch):

    def mock_local_unit():
        return 'mocked'

    monkeypatch.setattr('charmhelpers.core.hookenv.local_unit',
                        mock_local_unit)
    return mock_local_unit


@pytest.fixture
def mock_hookenv_config(monkeypatch):
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
def mock_remote_unit(monkeypatch):
    monkeypatch.setattr("lib_matrix.hookenv.remote_unit", lambda: "unit-mock/0")


@pytest.fixture
def mock_charm_dir(monkeypatch):
    monkeypatch.setattr("lib_matrix.hookenv.charm_dir", lambda: ".")


@pytest.fixture
def mock_template(monkeypatch):
    monkeypatch.setattr("lib_matrix.templating.host.os.fchown", mock.Mock())
    monkeypatch.setattr("lib_matrix.templating.host.os.chown", mock.Mock())
    monkeypatch.setattr("lib_matrix.templating.host.os.fchmod", mock.Mock())


@pytest.fixture
def mock_socket(monkeypatch):
    monkeypatch.setattr("lib_matrix.socket.getfqdn", lambda: "mock-host")


@pytest.fixture
def matrix(
    tmpdir, mock_hookenv_config, mock_charm_dir, mock_template, mock_socket, monkeypatch
):
    from lib_matrix import MatrixHelper

    helper = MatrixHelper()

    # Example config file patching
    homeserver_file = tmpdir.join("homeserver.yaml")
    helper.homeserver_config = homeserver_file.strpath

    # Any other functions that load helper will get this version
    monkeypatch.setattr("lib_matrix.MatrixHelper", lambda: helper)

    return helper
