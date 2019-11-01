#!/usr/bin/python3
"""Test the Matrix helper library."""

from charmhelpers.core import unitdata
import mock


def test_pytest():
    """Test that pytest itself works."""
    assert True


def test_matrix_fixture(matrix):
    """Test if the helper fixture works to load charm configs."""
    assert isinstance(matrix.charm_config, dict)


def test_matrix_kv(matrix):
    """Test if the helper fixture works to load KV store data."""
    assert isinstance(matrix.kv, unitdata.Storage)


def test_set_password(matrix, mock_check_call):
    """Test setting the password for a provided synapse user."""
    matrix.set_password("testuser",
                        "testpassword")
    assert matrix.hash_password.called_with("testpassword")
    assert matrix.pgsql_query.called_with("UPDATE users SET password_hash='testhash' WHEREname='testuser';")


def test_register_user(matrix):
    """Test creating a user with the provided credentials, with and without setting admin."""
    matrix.register_user("testuser",
                         "testpassword",
                         admin=True)
    assert matrix.hash_password.called_with("testpassword")
    assert matrix.pgsql_query.called_with(
        "INSERT INTO users (name, password, admin) VALUES ('testuser', 'testpassword', True);"
    )


def test_restart_synapse(matrix, mock_host):
    """Test restartingsynapse service."""
    matrix.synapse_service = "testservice"
    matrix.restart_synapse()
    assert mock_host.service_restart.called_with("testservice")
    assert mock_host.service_restart.call_count == 1


def test_restart(matrix, mock_host):
    """Restart services."""
    matrix.synapse_service = "testservice"
    matrix.restart_synapse()
    assert mock_host.service_restart.called_with("testservice")
    assert mock_host.service_restart.call_count == 1


def test_start_service(matrix, mock_host):
    """Start and enable the provided service, return run state."""
    matrix.synapse_service = "testservice"
    status = matrix.start_synapse()
    assert mock_host.service.called_with("testservice", "enable")
    assert mock_host.service.called_with("testservice", "start")
    assert mock_host.service.call_count == 2
    assert status is True


def start_services(matrix):
    """Configure and start services."""
    matrix.start_services()
    assert matrix.start_synapse.call_count == 1


def test_get_server_name(matrix, mock_socket):
    """Test get_server_name."""
    result = matrix.get_server_name()
    assert mock_socket.getfqdn.call_count == 1
    assert result == "mockhost"
    matrix.charm_config["server_name"] = "manualmockhost"
    result = matrix.get_server_name()
    assert result == "manualmockhost"


def test_get_tls(matrix):
    """Test returning the configured TLS state."""
    matrix.charm_config["enable-tls"] = True
    result = matrix.get_tls()
    assert result is True
    matrix.charm_config["enable-tls"] = False
    result = matrix.get_tls()
    assert result is False


def test_configure_proxy(matrix):
    """Test configure_proxy."""
    mock_proxy = mock.Mock()
    matrix.charm_config["enable-tls"] = False
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 80,
                "internal_host": "mockhost",
                "internal_port": 8008,
                "subdomain": "manualmockhost",
            }
        ]
    )

    # Test HTTPS
    mock_proxy.reset_mock()
    matrix.charm_config["enable-tls"] = True
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 443,
                "internal_host": "mockhost",
                "internal_port": 8008,
                "subdomain": "manualmockhost",
            }
        ]
    )


def test_remove_pgsql_conf(matrix):
    """Test remove pgsql_conf."""
    matrix.kv.set("db_host", "db_host")
    matrix.kv.set("db_port", "db_port")
    matrix.kv.set("db_db", "db_db")
    matrix.kv.set("db_user", "db_user")
    matrix.kv.set("db_pass", "db_pass")
    matrix.remove_pgsql_conf()
    assert not matrix.kv.get("db_host", None)
    assert not matrix.kv.get("db_port", None)
    assert not matrix.kv.get("db_db", None)
    assert not matrix.kv.get("db_user", None)


def test_save_pgsql_conf(matrix):
    """Test save_pgsql_conf."""
    db = mock.Mock()
    master = mock.Mock()
    master.host = "host"
    master.port = "port"
    master.dbname = "dbname"
    master.user = "user"
    master.password = "password"
    db.master = master
    matrix.save_pgsql_conf(db)
    assert matrix.kv.get("pgsql_host") == "host"
    assert matrix.kv.get("pgsql_port") == "port"
    assert matrix.kv.get("pgsql_db") == "dbname"
    assert matrix.kv.get("pgsql_user") == "user"
    assert matrix.kv.get("pgsql_pass") == "password"


def test_synapse_render_file(matrix, mock_templating, tmpdir):
    """Verify synapse template generation."""
    path = tmpdir.join("homeserver.yaml")
    matrix.homeserver_config = path
    matrix.charm_config["enable-tls"] = False
    matrix.charm_config["server-name"] = "mockhost"
    matrix.render_synapse_config()
    with open(matrix.homeserver_config, "rb") as config_file:
        content = config_file.readlines()
    assert b"server_name=mockhost\n" in content


def test_render_configs(matrix):
    """Test rendering of  configuration for the homeserver and enabled bridges."""
    matrix.charm_config["enable-irc"] = True
    matrix.charm_config["enable-slack"] = True
    matrix.render_configs()
    assert matrix.render_synapse_config.call_count == 1
    assert matrix.render_appservice_irc_config.call_count == 1
    assert matrix.render_appservice_slack_config.call_count == 1


def test_configure(matrix):
    """Test running the configure method."""
    matrix.render_configs()
    assert matrix.start_services.call_count == 1
