"""Helper class for configuring Matrix."""
import socket

from charmhelpers.core import hookenv, host, templating, unitdata
from charms.reactive.helpers import any_file_changed

# TODO: limits.conf file handle config
# TODO: template configuration
# TODO: handle reverse proxy relation
# TODO: handle DB relation
# TODO: handle apt sources and key
# TODO: handle package install
# TODO: handle federation bridges install
# TODO: libjemalloc


class MatrixHelper:
    """Helper class for installing, configuring and managing services for Matrix."""

    homeserver_config = "/var/snap/matrix-synapse/homeserver.yaml"
    synapse_service = "snap.matrix-synapse.matrix-synapse"

    HEALTHY = "Matrix homeserver installed and configured."

    def __init__(self):
        """Load hookenv key/value store and charm configuration."""
        self.charm_config = hookenv.config()
        self.kv = unitdata.kv()

    def set_password(self, user, password):
        """Set the password for a provided synapse user."""
        return True

    def register_user(self, user, password=None, admin=False):
        """Create a user with the provided credentials, and optionally set as an admin."""
        return True

    def restart_synapse(self):
        """Restart services."""
        host.service_restart(self.synapse_service)
        return True

    def restart(self):
        """Restart services."""
        self.restart_synapse()
        return True

    def start_service(self, service):
        """Start and enable the provided service, return run state."""
        host.service(service, "enable")
        host.service(service, "start")
        return host.service_running(service)

    def start_synapse(self):
        """Start and enable synapse."""
        synapse_running = self.start_service(self.synapse_service)
        return synapse_running

    def start_services(self):
        """Configure and start services."""
        self.start_synapse()

    def get_server_name(self):
        """Return the configured server name."""
        configured_value = self.charm_config["server-name"]
        if configured_value:
            return configured_value
        else:
            fqdn = socket.getfqdn()
            return fqdn

    def get_tls(self):
        """Return the configured TLS state."""
        configured_value = self.charm_config["enable-tls"]
        if configured_value:
            return configured_value
        else:
            fqdn = "http://{}".format(socket.getfqdn())
            return fqdn

    def configure_proxy(self, proxy):
        """Configure Synapse for operation behind a reverse proxy."""
        server_name = self.get_server_name()
        tls_enabled = self.get_tls()

        if tls_enabled:
            port = 443
        else:
            port = 80

        proxy_config = [
            {
                "mode": "http",
                "external_port": port,
                "internal_host": socket.getfqdn(),
                "internal_port": 8008,
                "subdomain": server_name,
            }
        ]
        proxy.configure(proxy_config)

    def pgsql_configured(self):
        """Determine if we have all requried DB configuration present."""
        if (
            self.kv.get("pgsql_host")
            and self.kv.get("pgsql_port")
            and self.kv.get("pgsql_db")
            and self.kv.get("pgsql_user")
            and self.kv.get("pgsql_pass")
        ):
            hookenv.log(
                "PostgreSQL is related and configured in the charm KV store",
                hookenv.DEBUG,
            )
            return True
        return False

    def redis_configured(self):
        """Determine if Redis is related and the KV has been updated with configuration."""
        if self.kv.get("redis_host") and self.kv.get("redis_port"):
            hookenv.log(
                "Redis is related and configured in the charm KV store", hookenv.DEBUG
            )
            return True
        return False

    def remove_mysql_conf(self):
        """Remove legacy MySQL configuraion from the unit KV store."""
        # legacy kv to clean up
        self.kv.unset("mysql_host")
        self.kv.unset("mysql_port")
        self.kv.unset("mysql_db")
        self.kv.unset("mysql_user")
        self.kv.unset("mysql_pass")

    def remove_pgsql_conf(self):
        """Remove the MySQL configuration from the unit KV store."""
        self.kv.unset("db_host")
        self.kv.unset("db_port")
        self.kv.unset("db_db")
        self.kv.unset("db_user")
        self.kv.unset("db_pass")

    def save_pgsql_conf(self, db):
        """Configure Matrix with knowledge of a related PostgreSQL endpoint."""
        hookenv.log(db, hookenv.DEBUG)
        if db:
            hookenv.log(
                "Saving related PostgreSQL database config: {}".format(db.master),
                hookenv.DEBUG,
            )
            self.kv.set("pgsql_host", db.master.host)
            self.kv.set("pgsql_port", db.master.port)
            self.kv.set("pgsql_db", db.master.dbname)
            self.kv.set("pgsql_user", db.master.user)
            self.kv.set("pgsql_pass", db.master.password)

    def render_synapse_config(self):
        """Render the configuration for Matrix synapse."""
        if self.pgsql_configured():
            templating.render(
                "homeserver.yaml.j2",
                self.homeserver_config,
                {
                    "db_host": self.kv.get("pgsql_host"),
                    "db_port": self.kv.get("pgsql_port"),
                    "db_database": self.kv.get("pgsql_db"),
                    "db_user": self.kv.get("pgsql_user"),
                    "db_password": self.kv.get("pgsql_pass"),
                    "server_name": self.get_server_name(),
                    "enable_tls": self.get_tls(),
                },
            )
        if any_file_changed([self.homeserver_config]):
            self.restart_synapse()
            return True
        return False

    def render_appservice_irc_config(self):
        """Render the configuration for Matrix synapse."""
        if self.pgsql_configured():
            templating.render(
                "homeserver.yaml.j2",
                self.homeserver_config,
                {
                    "db_host": self.kv.get("pgsql_host"),
                    "db_port": self.kv.get("pgsql_port"),
                    "db_database": self.kv.get("pgsql_db"),
                    "db_user": self.kv.get("pgsql_user"),
                    "db_password": self.kv.get("pgsql_pass"),
                    "server_name": self.get_server_name(),
                    "enable_tls": self.get_tls(),
                },
            )
        if any_file_changed([self.homeserver_config]):
            self.restart_synapse()
            return True
        return False

    def render_configs(self):
        """Render configuration for the homeserver and enabled bridges."""
        self.render_synapse_config()
        if self.charm_config.get("enable-irc"):
            self.render_appservice_irc_config()
        if self.charm_config.get("enable-slack"):
            self.render_appservice_slack_config()

    def configure(self):
        """
        Configure Matrix.

        Verified correct snaps are installed, renders
        configuration files and restarts services as needed.
        """
        self.render_configs()
        if self.start_services():
            hookenv.status_set("active", self.HEALTHY)
        else:
            hookenv.status_set("blocked", "Matrix services are not running.")
