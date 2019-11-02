"""Helper class for configuring Matrix."""
import socket
import random
import string

import psycopg2
from os import path
from subprocess import check_output

from charmhelpers.core import hookenv, host, templating, unitdata
from charms.reactive.helpers import any_file_changed
from signedjson.key import generate_signing_key, write_signing_keys

from charms.layer import snap


# TODO: limits.conf file handle config
# TODO: template configuration
# TODO: handle federation bridges install
# TODO: libjemalloc


class MatrixHelper:
    """Helper class for installing, configuring and managing services for Matrix."""

    homeserver_config = "/var/snap/matrix-synapse/common/homeserver.yaml"

    synapse_snap = "matrix-synapse"
    appservice_irc_snap = "matrix-appservice-irc"
    appservice_slack_snap = "matrix-appservice-slack"

    synapse_service = "snap.matrix-synapse.matrix-synapse"
    appservice_irc_service = "snap.matrix-appservice-irc.matrix-appservice-irc"
    appservice_slack_service = "snap.matrix-appservice-slack.matrix-appservice-slack"
    synapse_conf_dir = "/var/snap/matrix-synapse/common/"
    synapse_signing_key_file = None

    HEALTHY = "Matrix homeserver installed and configured."

    def __init__(self):
        """Load hookenv key/value store and charm configuration."""
        self.charm_config = hookenv.config()
        self.kv = unitdata.kv()
        if not self.synapse_signing_key_file:
            self.synapse_signing_key_file = "{}/{}.signing.key".format(
                self.synapse_conf_dir, self.get_server_name()
            )

    def hash_password(self, password):
        """Hash password using the synapse hash_password tool."""
        cmd = [
            "snap",
            "run",
            "{}.hash-password".format(self.synapse_snap),
            "-c",
            "/var/snap/{}/common/config.yaml".format(self.synapse_snap),
            "-p",
            "testpassword",
        ]
        return check_output(cmd)

    def set_password(self, user, password):
        """Set the password for a provided synapse user."""
        return True

    def register_user(self, user, password=None, admin=False):
        """Create a user with the provided credentials, and optionally set as an admin."""
        return True

    def pgsql_query(self, query, values=None):
        """Execute the provided query against the related database."""
        if self.pgsql_configured():
            connection = psycopg2.connect(
                host=self.kv.get("pgsql_host"),
                port=self.kv.get("pgsql_port"),
                database=self.kv.get("pgsql_db"),
                user=self.kv.get("pgsql_user"),
                password=self.kv.get("pgsql_pass"),
            )
            cursor = connection.cursor()
            try:
                result = cursor.execute(query, vars=values)
            except psycopg2.Error as e:
                hookenv.log(
                    "Error {} from PostgreSQL when executing query {}".format(
                        e.diag.message_primary, query
                    )
                )
                pass
            else:
                if result is None:
                    return True
                else:
                    return result
        return False

    def random_string(self, length):
        """Implement the random_string function from the synapse stringutils package."""
        return "".join(
            random.SystemRandom().choice(string.ascii_letters) for _ in range(length)
        )

    def get_synapse_signing_key(self):
        """Return the path of the synapse signing key, generating it if missing."""
        if not path.exists(self.synapse_signing_key_file):
            key_id = "a_" + self.random_string(4)
            key_content = generate_signing_key(key_id)
            with open(self.synapse_signing_key_file, "w+") as key_file:
                write_signing_keys(key_file, (key_content,))
        return self.synapse_signing_key_file

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
        host.service("start", self.synapse_service)
        host.service("enable", self.synapse_service)
        return host.service_running(service)

    def start_synapse(self):
        """Start and enable synapse."""
        synapse_running = self.start_service(self.synapse_service)
        return synapse_running

    def start_appservice_irc(self):
        """Start and enable the IRC bridge."""
        if self.charm_config.get("enable-irc"):
            irc_running = self.start_service(self.appservice_irc_service)
            return irc_running
        # this might seem silly, but if IRC is disabled the correct or 'True' state is that
        # the service is not running, so return True to indicate all is well
        return True

    def start_appservice_slack(self):
        """Start and enable the Slack bridge."""
        if self.charm_config.get("enable-slack"):
            slack_running = self.start_service(self.appservice_slack_service)
            return slack_running
        # this might also seem silly, but if Slack is disabled the correct or 'True' state is that
        # the service is not running, so return True to indicate all is well
        return True

    def start_services(self):
        """Configure and start services."""
        result = True
        result = self.start_synapse() and result
        result = self.start_appservice_irc() and result
        result = self.start_appservice_slack() and result
        return result

    def get_server_name(self):
        """Return the configured server name."""
        configured_value = self.charm_config["server-name"]
        if configured_value:
            return configured_value
        else:
            fqdn = socket.getfqdn()
            return fqdn

    def get_public_baseurl(self):
        """Return the public URI for this server."""
        server_name = self.get_server_name()
        tls = self.get_tls()
        if tls:
            return "https://{}".format(server_name)
        return "http://{}".format(server_name)

    def get_tls(self):
        """Return the configured TLS state."""
        configured_value = self.charm_config["enable-tls"]
        if configured_value:
            return configured_value
        return False

    def get_domain_whitelist(self):
        """Return dict of domains to whitelist based on comma separated charm config."""
        whitelist = self.charm_config["federation-domain-whitelist"]
        return list(filter(None, whitelist.split(",")))

    def get_federation_iprange_blacklist(self):
        """Return dict of ip ranges to blacklist based on comma separated charm config."""
        blacklist = self.charm_config["federation-ip-range-blacklist"]
        return list(filter(None, blacklist.split(",")))

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
        hookenv.log(
            "PostgreSQL is not yet configured in the charm KV store", hookenv.WARNING
        )
        return False

    def remove_pgsql_conf(self):
        """Remove the MySQL configuration from the unit KV store."""
        self.kv.unset("db_host")
        self.kv.unset("db_port")
        self.kv.unset("db_db")
        self.kv.unset("db_user")
        self.kv.unset("db_pass")

    def save_pgsql_conf(self, db):
        """Configure Matrix with knowledge of a related PostgreSQL endpoint."""
        hookenv.log(
            "Checking related DB information before saving PostgreSQL configuration",
            hookenv.DEBUG,
        )
        if db:
            hookenv.log("Saving related PostgreSQL database config", hookenv.DEBUG)
            self.kv.set("pgsql_host", db.master.host)
            self.kv.set("pgsql_port", db.master.port)
            self.kv.set("pgsql_db", db.master.dbname)
            self.kv.set("pgsql_user", db.master.user)
            self.kv.set("pgsql_pass", db.master.password)

    def render_synapse_config(self):
        """Render the configuration for Matrix synapse."""
        hookenv.log(
            "Rendering synapse configuration to {}".format(self.homeserver_config),
            hookenv.DEBUG,
        )
        if self.pgsql_configured():
            templating.render(
                "homeserver.yaml.j2",
                self.homeserver_config,
                {
                    "conf_dir": self.synapse_conf_dir,
                    "signing_key": self.get_synapse_signing_key(),
                    "pgsql_configured": self.pgsql_configured(),
                    "pgsql_host": self.kv.get("pgsql_host"),
                    "pgsql_port": self.kv.get("pgsql_port"),
                    "pgsql_db": self.kv.get("pgsql_db"),
                    "pgsql_user": self.kv.get("pgsql_user"),
                    "pgsql_pass": self.kv.get("pgsql_pass"),
                    "server_name": self.get_server_name(),
                    "public_baseurl": self.get_public_baseurl(),
                    "enable_tls": self.get_tls(),
                    "enable_search": self.charm_config["enable-search"],
                    "enable_user_directory": self.charm_config["enable-user-directory"],
                    "enable_room_list_search": self.charm_config[
                        "enable-room-list-search"
                    ],
                    "enable_registration": self.charm_config["enable-registration"],
                    "use_presence": self.charm_config["track-presence"],
                    "require_auth_for_profile_requests": self.charm_config[
                        "require-auth-profile-requests"
                    ],
                    "default_room_version": self.charm_config["default-room-version"],
                    "block_non_admin_invites": not bool(
                        self.charm_config["enable-non-admin-invites"]
                    ),
                    "report_stats": self.charm_config["enable-reporting-stats"],
                    "allow_public_rooms_without_auth": self.charm_config[
                        "allow-public-rooms-unauthed"
                    ],
                    "allow_public_rooms_over_federation": self.charm_config[
                        "allow-public-rooms-federated"
                    ],
                    "federation_domain_whitelist": self.get_domain_whitelist(),
                    "federation_ip_range_blacklist": self.get_federation_iprange_blacklist(),
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
        else:
            hookenv.log(
                "Skipped rendering synapse configuration due to unconfigured pgsql",
                hookenv.DEBUG,
            )
        if any_file_changed([self.homeserver_config]):
            self.restart_synapse()
            return True
        return False

    def render_appservice_slack_config(self):
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
        else:
            hookenv.log(
                "Skipped rendering synapse configuration due to unconfigured pgsql",
                hookenv.DEBUG,
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

    def check_snap_installed(self, snapname):
        """Verify a snap is installed."""
        return snap.is_installed(snapname)

    def install_snap(self, snapname):
        """Install specific snap."""
        snap.install(snapname)

    def remove_snap(self, snapname):
        """Remove specific snap."""
        snap.remove(snapname)

    def install_snaps(self):
        """Install snaps for configured briges."""
        result = True
        if not self.check_snap_installed(self.synapse_snap):
            hookenv.log("Installing {} snap".format(self.synapse_snap), hookenv.DEBUG)
            result = self.install_snap(self.synapse_snap) and result
        irc_installed = self.check_snap_installed(self.appservice_irc_snap)
        if self.charm_config.get("enable-irc"):
            if not irc_installed:
                hookenv.log(
                    "Installing {} snap".format(self.appservice_irc_snap), hookenv.DEBUG
                )
                result = self.install_snap(self.appservice_irc_snap) and result
        elif irc_installed:
            self.remove_snap(self.appservice_irc_snap)
        # TODO: additional bridges
        if result:
            hookenv.log("Snaps are installed.", hookenv.DEBUG)
        return result

    def configure(self):
        """
        Configure Matrix.

        Verified correct snaps are installed, renders
        configuration files and restarts services as needed.
        """
        if self.install_snaps:
            self.render_configs()
            if self.start_services():
                hookenv.status_set("active", self.HEALTHY)
                return True
            else:
                hookenv.status_set("blocked", "Matrix services are not running.")
        else:
            hookenv.status_set(
                "blocked",
                "Snaps are not installable. Check snap store accessibility or that resources are uploaded.",
            )
        return False
