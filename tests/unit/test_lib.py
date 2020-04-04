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


def test_hash_password(matrix, mock_check_output):
    """Test the hash password function."""
    result = matrix.hash_password("testpassword")
    assert result == "mocked-output"


def test_pgsql_configured(matrix):
    """Test the pgsql_configured routine."""
    result = matrix.pgsql_configured()
    assert result is False
    matrix.kv.set("pgsql_user", "test")
    matrix.kv.set("pgsql_db", "test")
    matrix.kv.set("pgsql_pass", "test")
    matrix.kv.set("pgsql_host", "test.test.test")
    matrix.kv.set("pgsql_port", 1234)
    result = matrix.pgsql_configured()
    assert result is True


def test_pgsql_query(matrix, mock_psycopg2):
    """Test the pgsql_query function."""
    result = matrix.pgsql_query("SELECT * from users;")
    assert result is True


def test_set_password(matrix, mock_check_output, mock_psycopg2):
    """Test setting the password for a provided synapse user."""
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


def test_register_user(matrix, mock_check_output, mock_psycopg2):
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
            "http://mockhost:8008",
        ]
    )
    assert mock_check_output.call_count == 1


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
    assert result == "mockhost"
    matrix.charm_config["server-name"] = "manualmockhost"
    result = matrix.get_server_name()
    assert result == "manualmockhost"


def test_baseurl(matrix):
    """Test the get_public_baseurl function."""
    matrix.charm_config["enable-tls"] = False
    result = matrix.get_public_baseurl()
    assert result == "http://mockhost:8008"
    matrix.charm_config["enable-tls"] = False
    matrix.external_port = 80
    result = matrix.get_public_baseurl()
    assert result == "http://mockhost"
    matrix.charm_config["enable-tls"] = True
    result = matrix.get_public_baseurl()
    assert result == "https://mockhost"


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
                "subdomain": "mockhost",
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
                "subdomain": "mockhost",
            }
        ]
    )

    # Test manual server name
    mock_proxy.reset_mock()
    matrix.charm_config["enable-tls"] = False
    matrix.charm_config["server-name"] = "manual.mock.host"
    matrix.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == mock.call(
        [
            {
                "mode": "http",
                "external_port": 80,
                "internal_host": "mockhost",
                "internal_port": 8008,
                "subdomain": "manual.mock.host",
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


def test_render_synapse_config(matrix, tmpdir):
    """Test rendering of configuration for the homeserver."""
    path = tmpdir.join("homeserver.yaml")
    matrix.synapse_config = path
    matrix.charm_config["enable-tls"] = False
    matrix.charm_config["server-name"] = "manual.mock.host"
    matrix.render_configs()
    with open(matrix.synapse_config, "rb") as config_file:
        content = config_file.readlines()
    print(content)
    assert b'server_name: "manual.mock.host"\n' in content


def test_configure(matrix):
    """Test running the configure method."""
    result = matrix.configure()
    assert result is True
    matrix.synapse_service = "failing-service"
    matrix.synapse_snap = "bad-snap"
    result = matrix.configure()
    assert result is False
    matrix.synapse_service = "snap.matrix-synapse.matrix-synapse"
    matrix.synapse_snap = "installed-snap"
    result = matrix.configure()
    assert result is True
