#!/usr/bin/python3
"""Test the Matrix helper library."""

from charmhelpers.core import unitdata
import mock
import os


db = mock.Mock()
master = mock.Mock()
master.host = "host"
master.port = "port"
master.dbname = "dbname"
master.user = "user"
master.password = "password"
db.master = master


def test_pytest():
    """Test that pytest itself works."""
    assert True


def test_matrix_fixture(matrix):
    """Test if the helper fixture works to load charm configs."""
    assert isinstance(matrix.charm_config, dict)


def test_matrix_kv(matrix):
    """Test if the helper fixture works to load KV store data."""
    assert isinstance(matrix.kv, unitdata.Storage)


def test_hash_password(matrix, mock_check_output):
    """Test the hash password function."""
    result = matrix.hash_password("testpassword")
    assert result == "mocked-output"


def test_pgsql_configured(matrix):
    """Test the pgsql_configured routine."""
    matrix.remove_pgsql_conf()
    result = matrix.pgsql_configured()
    assert result is False
    matrix.save_pgsql_conf(db)
    result = matrix.pgsql_configured()
    assert result is True


def test_pgsql_query(matrix, mock_psycopg2):
    """Test the pgsql_query function."""
    result = matrix.pgsql_query("SELECT * from users;")
    assert result is False
    matrix.save_pgsql_conf(db)
    result = matrix.pgsql_query("SELECT * from users;")
    assert result is True


def test_set_password(matrix, mock_check_output, mock_psycopg2):
    """Test setting the password for a provided synapse user."""
    matrix.save_pgsql_conf(db)
    matrix.set_password("testuser", "testpassword")
    assert mock_check_output.called_with(
        [
            "snap",
            "run",
            "{}.hash_password".format(matrix.synapse_snap),
            "-c",
            matrix.synapse_config,
            "-p",
            "testpassword",
        ]
    )
    assert mock_check_output.call_count == 1
    assert mock_psycopg2.Cursor.execute.called_with(
        "UPDATE users SET password_hash='testhash' WHERE name='testuser';"
    )
    assert mock_psycopg2.Cursor.execute.call_count == 1


def test_register_user(matrix, mock_check_output, mock_psycopg2, mock_random):
    """Test creating a user with the provided credentials, with and without setting admin."""
    matrix.register_user("testuser", "testpassword", admin=True)
    assert mock_check_output.called_with(
        [
            "snap",
            "run",
            "{}.register-new-matrix-user".format(matrix.synapse_snap),
            "-u",
            "testuser",
            "-p",
            "testpassword",
            "-a",
            "-c",
            matrix.synapse_config,
            "http://mock.fqdn:8008",
        ]
    )
    assert mock_check_output.call_count == 1
    matrix.register_user("testuser2")
    assert mock_check_output.called_with(
        [
            "snap",
            "run",
            "{}.register-new-matrix-user".format(matrix.synapse_snap),
            "-u",
            "testuser2",
            "-p",
            "mmmmmmmmmmmmmmmm",
            "-c",
            matrix.synapse_config,
            "http://mock.fqdn:8008",
        ]
    )
    assert mock_check_output.call_count == 2


def test_get_secret(matrix, mock_random):
    """Test secret generation."""
    matrix.kv.unset("shared-secret")
    secret = matrix.get_shared_secret()
    assert secret == "mmmmmmmmmmmmmmmm"


def test_get_token(matrix, mock_random):
    """Test shared secret."""
    matrix.kv.unset("mock-token")
    result = matrix.get_token("mock-token")
    assert result == "mmmmmmmmmmmmmmmmmmmmmmmm"
    result = matrix.get_token("mock-token")
    assert result == "mmmmmmmmmmmmmmmmmmmmmmmm"


def test_restart(matrix, mock_host_service):
    """Restart services."""
    matrix.synapse_service = "testservice"
    matrix.restart()
    assert mock_host_service.called_with("restart", "testservice")
    assert mock_host_service.call_count == 1


def test_start_services(matrix, mock_host_service):
    """Configure and start services."""
    mock_host_service.reset_mock()
    status = matrix.start_services()
    mock_host_service.assert_has_calls(
        [
            mock.call("start", matrix.synapse_service),
            mock.call("enable", matrix.synapse_service),
        ],
        any_order=False,
    )
    assert mock_host_service.call_count == 2
    assert status is True


def test_get_server_name(matrix, mock_socket):
    """Test get_server_name."""
    result = matrix.get_server_name()
    assert result == "mock.fqdn"
    matrix.charm_config["server-name"] = "manualmockhost"
    result = matrix.get_server_name()
    assert result == "manualmockhost"


def test_baseurl(matrix):
    """Test the get_public_baseurl function."""
    matrix.charm_config["enable-tls"] = False
    result = matrix.get_public_baseurl()
    assert result == "http://mock.fqdn:8008"
    matrix.charm_config["enable-tls"] = False
    matrix.external_port = 80
    result = matrix.get_public_baseurl()
    assert result == "http://mock.fqdn"
    matrix.charm_config["enable-tls"] = True
    result = matrix.get_public_baseurl()
    assert result == "https://mock.fqdn"


def test_get_tls(matrix):
    """Test returning the configured TLS state."""
    matrix.charm_config["enable-tls"] = True
    result = matrix.get_tls()
    assert result is True
    matrix.charm_config["enable-tls"] = False
    result = matrix.get_tls()
    assert result is False


def test_get_federation(matrix):
    """Test getting federation state."""
    matrix.charm_config["enable-federation"] = False
    result = matrix.get_federation()
    assert result is False
    matrix.charm_config["enable-federation"] = True
    result = matrix.get_federation()
    assert result is True


def test_configure_proxy(matrix):
    """Test configure_proxy with internal IP preference but no internal host preference."""
    mock_proxy = mock.Mock()
    matrix.charm_config["enable-tls"] = False
    matrix.charm_config["enable-federation"] = False
    matrix.charm_config["external-domain"] = "mock.external"
    matrix.charm_config["prefer-internal-ip"] = True
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 80,
                "internal_host": "10.10.10.10",
                "internal_port": 8008,
                "subdomain": "mock.external",
            }
        ]
    )

    """Test configure_proxy with internal IP preference and internal host preference."""
    mock_proxy = mock.Mock()
    matrix.charm_config["enable-tls"] = False
    matrix.charm_config["enable-federation"] = False
    matrix.charm_config["external-domain"] = "mock.external"
    matrix.charm_config["prefer-internal-ip"] = True
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 80,
                "internal_host": "10.10.10.10",
                "internal_port": 8008,
                "subdomain": "mock.external",
            }
        ]
    )

    """Test configure_proxy."""
    mock_proxy = mock.Mock()
    matrix.charm_config["enable-tls"] = False
    matrix.charm_config["enable-federation"] = False
    matrix.charm_config["external-domain"] = ""
    matrix.charm_config["prefer-internal-ip"] = False
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 80,
                "internal_host": "mock.fqdn",
                "internal_port": 8008,
                "subdomain": "mock.fqdn",
            }
        ]
    )

    """Test configure_proxy with manual external domain."""
    mock_proxy = mock.Mock()
    matrix.charm_config["enable-tls"] = False
    matrix.charm_config["enable-federation"] = False
    matrix.charm_config["external-domain"] = "matrix.mockhost"
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 80,
                "internal_host": "mock.fqdn",
                "internal_port": 8008,
                "subdomain": "matrix.mockhost",
            }
        ]
    )

    # Test HTTPS
    mock_proxy.reset_mock()
    matrix.charm_config["enable-tls"] = True
    matrix.charm_config["enable-federation"] = False
    matrix.charm_config["external-domain"] = ""
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 443,
                "internal_host": "mock.fqdn",
                "internal_port": 8008,
                "subdomain": "mock.fqdn",
            }
        ]
    )

    # Test manual server name
    mock_proxy.reset_mock()
    matrix.charm_config["enable-tls"] = False
    matrix.charm_config["enable-federation"] = False
    matrix.charm_config["server-name"] = "manual.mock.host"
    matrix.charm_config["external-domain"] = ""
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 80,
                "internal_host": "mock.fqdn",
                "internal_port": 8008,
                "subdomain": "manual.mock.host",
            }
        ]
    )

    # Test manual server name with external domain specified
    mock_proxy.reset_mock()
    matrix.charm_config["enable-tls"] = False
    matrix.charm_config["enable-federation"] = False
    matrix.charm_config["server-name"] = "manual.mock.host"
    matrix.charm_config["external-domain"] = "matrix.manual.mock.host"
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 80,
                "internal_host": "mock.fqdn",
                "internal_port": 8008,
                "subdomain": "matrix.manual.mock.host",
            }
        ]
    )

    # Test HTTPS with federation enabled
    mock_proxy.reset_mock()
    matrix.charm_config["enable-tls"] = True
    matrix.charm_config["enable-federation"] = True
    matrix.charm_config["server-name"] = ""
    matrix.charm_config["external-domain"] = ""
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 443,
                "internal_host": "mock.fqdn",
                "internal_port": 8008,
                "subdomain": "mock.fqdn",
            },
            {
                "mode": "tcp+tls",
                "external_port": 8448,
                "internal_host": "mock.fqdn",
                "internal_port": 8448,
            }
        ]
    )

    # Test HTTPS with federation enabled and manual server name
    mock_proxy.reset_mock()
    matrix.charm_config["enable-tls"] = True
    matrix.charm_config["enable-federation"] = True
    matrix.charm_config["server-name"] = "manual.mock.host"
    matrix.charm_config["external-domain"] = ""
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 443,
                "internal_host": "mock.fqdn",
                "internal_port": 8008,
                "subdomain": "manual.mock.host",
            },
            {
                "mode": "tcp+tls",
                "external_port": 8448,
                "internal_host": "mock.fqdn",
                "internal_port": 8448,
            }
        ]
    )

    # Test HTTPS with federation enabled
    mock_proxy.reset_mock()
    matrix.charm_config["enable-tls"] = True
    matrix.charm_config["enable-federation"] = True
    matrix.charm_config["server-name"] = "manual.mock.host"
    matrix.charm_config["external-domain"] = "matrix.manual.mock.host"
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 443,
                "internal_host": "mock.fqdn",
                "internal_port": 8008,
                "subdomain": "matrix.manual.mock.host",
            },
            {
                "mode": "tcp+tls",
                "external_port": 8448,
                "internal_host": "mock.fqdn",
                "internal_port": 8448,
            }
        ]
    )

    # Test IRC with TLS enabled
    mock_proxy.reset_mock()
    matrix.charm_config["enable-tls"] = True
    matrix.charm_config["enable-federation"] = True
    matrix.charm_config["server-name"] = "manual.mock.host"
    matrix.charm_config["external-domain"] = "matrix.manual.mock.host"
    matrix.charm_config["enable-ircd"] = True
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 443,
                "internal_host": "mock.fqdn",
                "internal_port": 8008,
                "subdomain": "matrix.manual.mock.host",
            },
            {
                "mode": "tcp+tls",
                "external_port": 8448,
                "internal_host": "mock.fqdn",
                "internal_port": 8448,
            },
            {
                "mode": "tcp+tls",
                "external_port": 6697,
                "internal_host": "mock.fqdn",
                "internal_port": 6667,
            },
        ]
    )

    # Test IRC without TLS enabled
    mock_proxy.reset_mock()
    matrix.charm_config["enable-tls"] = False
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 80,
                "internal_host": "mock.fqdn",
                "internal_port": 8008,
                "subdomain": "matrix.manual.mock.host",
            },
            {
                "mode": "tcp",
                "external_port": 8448,
                "internal_host": "mock.fqdn",
                "internal_port": 8448,
            },
            {
                "mode": "tcp",
                "external_port": 6667,
                "internal_host": "mock.fqdn",
                "internal_port": 6667,
            },
        ]
    )


def test_remove_proxy(matrix):
    """Test removal of reverse proxy."""
    matrix.remove_proxy_config()
    assert matrix.external_port == 8008


def test_remove_pgsql_conf(matrix):
    """Test remove pgsql_conf."""
    db = mock.Mock()
    master = mock.Mock()
    master.host = "host"
    master.port = "port"
    master.dbname = "dbname"
    master.user = "user"
    master.password = "password"
    db.master = master
    matrix.save_pgsql_conf(db)
    matrix.remove_pgsql_conf()
    assert not matrix.kv.get("pgsql_host", None)
    assert not matrix.kv.get("pgsql_port", None)
    assert not matrix.kv.get("pgsql_db", None)
    assert not matrix.kv.get("pgsql_user", None)
    result = matrix.pgsql_configured()
    assert result is False


def test_save_pgsql_conf(matrix):
    """Test save_pgsql_conf."""
    matrix.save_pgsql_conf(db)
    assert matrix.kv.get("pgsql_host") == "host"
    assert matrix.kv.get("pgsql_port") == "port"
    assert matrix.kv.get("pgsql_db") == "dbname"
    assert matrix.kv.get("pgsql_user") == "user"
    assert matrix.kv.get("pgsql_pass") == "password"
    result = matrix.pgsql_configured()
    assert result is True


def test_get_irc_port(matrix):
    """Test IRC port logic."""
    matrix.charm_config["enable-tls"] = True
    assert matrix.get_irc_port() == 6697
    matrix.charm_config["enable-tls"] = False
    assert matrix.get_irc_port() == 6667


def test_get_irc_mode(matrix):
    """Test IRC port logic."""
    matrix.charm_config["enable-tls"] = True
    assert matrix.get_irc_mode() == "tcp+tls"
    matrix.charm_config["enable-tls"] = False
    assert matrix.get_irc_mode() == "tcp"


def test_get_internal_url(matrix):
    """Test getting internal URLs."""
    matrix.charm_config["prefer-internal-ip"] = True
    matrix.charm_config["prefer-internal-host"] = True
    assert matrix.get_internal_url() == "http://10.10.10.10:8008"
    matrix.charm_config["prefer-internal-ip"] = False
    assert matrix.get_internal_url() == "http://mock.fqdn:8008"


def test_get_internal_host(matrix):
    """Test getting internal host name or IP."""
    matrix.charm_config["prefer-internal-ip"] = True
    matrix.charm_config["prefer-internal-host"] = True
    assert matrix.get_internal_host() == "10.10.10.10"
    matrix.charm_config["prefer-internal-ip"] = False
    assert matrix.get_internal_host() == "mock.fqdn"


def test_render_synapse_config(matrix, tmpdir):
    """Test rendering of configuration for the homeserver."""
    path = tmpdir.join("homeserver.yaml")
    matrix.synapse_config = path
    matrix.charm_config["enable-tls"] = False
    matrix.charm_config["server-name"] = "manual.mock.host"
    matrix.render_configs()
    assert not os.path.exists(matrix.synapse_config)
    matrix.save_pgsql_conf(db)
    matrix.render_configs()
    with open(matrix.synapse_config, "rb") as config_file:
        content = config_file.readlines()
    print(content)
    assert b'server_name: "manual.mock.host"\n' in content


def test_configure(matrix, mock_snap):
    """Test running the configure method."""
    matrix.charm_config["enable-ircd"] = True
    assert mock_snap.install.call_count == 0
    assert mock_snap.is_installed.call_count == 0
    assert mock_snap.remove.call_count == 0

    result = matrix.configure()
    assert mock_snap.install.call_count == 0
    assert mock_snap.is_installed.call_count == 2
    assert mock_snap.remove.call_count == 0
    assert result is False

    mock_snap.install.reset_mock()
    mock_snap.is_installed.reset_mock()
    mock_snap.remove.reset_mock()

    matrix.save_pgsql_conf(db)
    matrix.synapse_service = "fail-service"
    matrix.synapse_snap = "fail-snap"
    matrix.matrix_ircd_snap = "matrix-ircd"
    result = matrix.configure()
    assert result is False
    assert mock_snap.install.called_with("matrix-ircd")
    assert mock_snap.is_installed.called_with("matrix-ircd")
    assert mock_snap.install.call_count == 1
    assert mock_snap.is_installed.call_count == 2
    assert mock_snap.remove.call_count == 0

    matrix.synapse_service = "snap.matrix-synapse.matrix-synapse"
    matrix.synapse_snap = "matrix-synapse"
    result = matrix.configure()
    assert result is True

    matrix.charm_config["enable-ircd"] = False
    result = matrix.configure()
    assert result is True
    assert mock_snap.remove.call_count == 1
    assert mock_snap.install.called_with("matrix-ircd")

    mock_snap.install.reset_mock()
    mock_snap.is_installed.reset_mock()
    mock_snap.remove.reset_mock()

    matrix.charm_config["enable-ircd"] = True
    matrix.matrix_ircd_service = "fail-service"
    result = matrix.configure()
    assert result is False
    assert mock_snap.install.called_with("matrix-ircd")
    assert mock_snap.is_installed.called_with("matrix-ircd")
    assert mock_snap.install.call_count == 0
    assert mock_snap.is_installed.call_count == 2
    assert mock_snap.remove.call_count == 0

    matrix.matrix_ircd_service = "snap.matrix-ircd.matrix-ircd"
    matrix.matrix_ircd_snap = "fail-snap"
    result = matrix.configure()
    assert result is False

    matrix.matrix_ircd_snap = "matrix-ircd"
    matrix.matrix_ircd_service = "fail-service"
    result = matrix.configure()
    assert result is False

    matrix.matrix_ircd_service = "snap.matrix-ircd.matrix-ircd"
    result = matrix.configure()
    assert result is True

    matrix.remove_pgsql_conf()
    result = matrix.pgsql_configured()
    assert matrix.pgsql_configured() is False

    result = matrix.configure()
    assert result is False
