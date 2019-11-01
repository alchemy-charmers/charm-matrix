#!/usr/bin/python3
import mock
import pytest


# If layer options are used, add this to pihole
# and import layer in lib_pi_hole
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

    monkeypatch.setattr("lib_pi_hole.layer.options", options)


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

    monkeypatch.setattr("lib_pi_hole.hookenv.config", mock_config)


@pytest.fixture
def mock_remote_unit(monkeypatch):
    monkeypatch.setattr("lib_pi_hole.hookenv.remote_unit", lambda: "unit-mock/0")


@pytest.fixture
def mock_charm_dir(monkeypatch):
    monkeypatch.setattr("lib_pi_hole.hookenv.charm_dir", lambda: ".")


@pytest.fixture
def mock_template(monkeypatch):
    monkeypatch.setattr("lib_pi_hole.templating.host.os.fchown", mock.Mock())
    monkeypatch.setattr("lib_pi_hole.templating.host.os.chown", mock.Mock())
    monkeypatch.setattr("lib_pi_hole.templating.host.os.fchmod", mock.Mock())


@pytest.fixture
def mock_socket(monkeypatch):
    monkeypatch.setattr("lib_pi_hole.socket.getfqdn", lambda: "mock-host")


@pytest.fixture
def mock_subprocess(monkeypatch):
    mock_subprocess = mock.Mock()
    monkeypatch.setattr("lib_pi_hole.subprocess", mock_subprocess)
    return mock_subprocess


@pytest.fixture
def pihole(
    tmpdir,
    mock_hookenv_config,
    mock_charm_dir,
    mock_template,
    mock_socket,
    mock_subprocess,
    monkeypatch,
):
    from lib_pi_hole import PiholeHelper

    helper = PiholeHelper()

    # Example config file patching
    setup_vars_file = tmpdir.join("setupVars.conf")
    helper.setup_vars_file = setup_vars_file.strpath
    stubby_file = tmpdir.join("stubby.yml")
    helper.stubby_file = stubby_file.strpath
    unbound_file = tmpdir.join("pihole.conf")
    helper.unbound_file = unbound_file.strpath
    pihole_extra_file = tmpdir.join("02-pihole-extra.conf")
    helper.pihole_extra_file = pihole_extra_file.strpath

    # mocked functions
    helper.mock_subprocess = mock_subprocess

    # Any other functions that load helper will get this version
    monkeypatch.setattr("lib_pi_hole.PiholeHelper", lambda: helper)

    return helper
