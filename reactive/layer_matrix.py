"""Matrix helper class for reactive charm layer."""
from charms.layer import snap
from lib_matrix import MatrixHelper
from charmhelpers.core import hookenv
from charms.reactive import (
    clear_flag,
    endpoint_from_flag,
    endpoint_from_name,
    set_flag,
    when,
    when_all,
    when_any,
    when_not,
)


matrix = MatrixHelper()


@when_not("snap.installed.matrix-synapse")
def install_matrix_synapse():
    """Installs matrix synapse snap."""
    hookenv.status_set("maintenance", "Installing Matrix")
    snap.install("matrix-synapse")
    hookenv.status_set("active", "Matrix Installed")


@when("pgsql.database.connected")
def set_pgsql_db():
    """Set PostgreSQL database name, so the related charm will create the DB for us."""
    hookenv.log("Requesting matrix DB from {}".format(hookenv.remote_unit()),
                hookenv.DEBUG)
    pgsql = endpoint_from_flag("pgsql.database.connected")
    pgsql.set_database(matrix.db_name)


@when("pgsql.database.available")
def save_pgsql_db():
    """Save PostgreSQL data configuration in the key value store."""
    pgsql = endpoint_from_flag("pgsql.database.available")
    hookenv.log("Recieved matrix DB from PostgreSQL: {}".format(pgsql),
                hookenv.DEBUG)
    matrix.save_pgsql_conf(pgsql)


@when_any("pgsql.departed")
def remove_pgsql():
    """Remove the PostgreSQL DB configuration when the relation has been removed."""
    hookenv.status_set("maintenance", "Cleaning up removed pgsql relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))
    matrix.remove_pgsql_conf()


@when("reverseproxy.departed")
def remove_proxy():
    """Remove the haproxy configuration when the relation is removed."""
    hookenv.status_set("maintenance", "Removing reverse proxy relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()),
                hookenv.DEBUG)
    matrix.remove_proxy_config()
    hookenv.status_set("active", matrix.HEALTHY)
    clear_flag("reverseproxy.configured")


@when("pgsql.database.connected")
@when_not("pgsql.database.available")
def wait_pgsql():
    """Update charm status while waiting for PostgreSQL to be ready."""
    hookenv.status_set("blocked", "Waiting for PostgreSQL database")


@when_not("pgsql.database.available")
def missing_db_relation():
    """Complains if the PostgreSQL relation is missing."""
    hookenv.status_set("blocked", "Missing relation to PostgreSQL")


@when("reverseproxy.ready")
@when_not("reverseproxy.configured")
def configure_proxy():
    """Configure reverse proxy settings when haproxy is related."""
    hookenv.status_set("maintenance", "Applying reverse proxy configuration")
    hookenv.log("Configuring reverse proxy via: {}".format(hookenv.remote_unit()), hookenv.DEBUG)

    interface = endpoint_from_name("reverseproxy")
    matrix.configure_proxy(interface)

    hookenv.status_set("active", matrix.HEALTHY)
    set_flag("reverseproxy.configured")


@when_all("snap.installed.matrix-synapse", "pgsql.database.available")
@when_any("config.changed", "pgsql.database.changed")
def configure_matrix(reverseproxy, *args):
    """Upgrade and reconfigure matrix on configuration changes.

    Templaes the homeserver and assosciated bridge
    configuration, ensures snaps are installed and updates,
    and services running.
    """
    hookenv.status_set("maintenance", "Configuring matrix")
    hookenv.log("Configuring matrix", hookenv.DEBUG)

    matrix.configure()
