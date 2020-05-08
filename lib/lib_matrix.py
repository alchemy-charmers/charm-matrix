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
# TODO: handle federation bridges install
# TODO: libjemalloc


class MatrixHelper:
    """Helper class for installing, configuring and managing services for Matrix."""

    synapse_config = "/var/snap/matrix-synapse/common/homeserver.yaml"

    synapse_snap = "matrix-synapse"

    synapse_service = "snap.matrix-synapse.matrix-synapse"

    synapse_conf_dir = "/var/snap/matrix-synapse/common/"
    synapse_signing_key_file = None

    db_name = "matrix"

    external_port = 8008

    HEALTHY = "Matrix homeserver installed and configured"

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
            self.synapse_config,
            "-p",
            password,
        ]
        result = check_output(cmd)
        str_result = result.decode("utf-8")
        return str_result.rstrip()

    def set_password(self, user, password):
        """Set the password for a provided synapse user."""
        hashed_password = self.hash_password(password)
        server_name = self.get_server_name()
        hookenv.log("Storing hash: {}".format(hashed_password), hookenv.DEBUG)
        result = self.pgsql_query(
            "UPDATE users SET password_hash = '{}' WHERE name = '@{}:{}';".format(
                hashed_password, user, server_name
            )
        )
        return result

    def register_user(self, user, password=None, admin=False):
        """Create a user with the provided credentials, and optionally set as an admin."""
        if not password:
            password = self.random_string(16)
        admin_flag = "--no-admin"
        if admin:
            admin_flag = "-a"
        hookenv.log("Registering user {}".format(user), hookenv.DEBUG)
        cmd = [
            "snap",
            "run",
            "{}.register-new-matrix-user".format(self.synapse_snap),
            "-u",
            user,
            "-p",
            password,
            admin_flag,
            "-c",
            self.synapse_config,
            self.get_public_baseurl(),
        ]
        result = check_output(cmd)
        return result

    def pgsql_query(self, query, values=None):
        """Execute the provided query against the related database."""
        if self.pgsql_configured():
            connection = psycopg2.connect(
                host=self.kv.get("pgsql_host"),
                port=self.kv.get("pgsql_port"),
                dbname=self.kv.get("pgsql_db"),
                user=self.kv.get("pgsql_user"),
                password=self.kv.get("pgsql_pass"),
            )
            connection.set_session(autocommit=True)
            cursor = connection.cursor()
            try:
                hookenv.log(
                    "Executing query {} with values {}".format(query, values),
                    hookenv.DEBUG,
                )
                result = cursor.execute(query, vars=values)
            except psycopg2.Error as e:
                hookenv.log(
                    "Error {} from PostgreSQL when executing query {}".format(
                        e.diag.message_primary, query
                    ),
                    hookenv.ERROR,
                )
                return e.diag.message_primary
            hookenv.log("Query result: {}".format(result), hookenv.DEBUG)
            cursor.close()
            connection.close()
            return result

    def pgsql_create_db(self, name):
        """Create the named PostgreSQL database."""
        flag = "pgsql_created_{}".format(name)
        if self.pgsql_configured():
            if self.kv.get(flag):
                return True
            else:
                create_result = self.pgsql_query(
                    "CREATE DATABASE {0} OWNER postgres".format(name)
                )
                grant_result = self.pgsql_query(
                    "GRANT ALL PRIVILEGES ON DATABASE {0} TO {1}".format(
                        name, self.kv.get("pgsql_user")
                    )
                )
                hookenv.log(
                    "DB Create: {}, Grant: {}".format(create_result, grant_result),
                    hookenv.DEBUG,
                )
                if create_result is None and grant_result is None:
                    self.kv.set("pgsql_created_{}".format(name), True)
                    return create_result
        return False

    def random_string(self, length):
        """Implement the random_string function from the synapse stringutils package."""
        return "".join(
            random.SystemRandom().choice(string.ascii_letters) for _ in range(length)
        )

    def get_token(self, name):
        """
        Return a 24 character token.

        The token will be stored in KV as the provided
        name and returned from KV is preexisting.
        """
        if self.kv.get(name):
            return self.kv.get(name)
        token = self.random_string(24)
        self.kv.set(name, token)
        return token

    def get_shared_secret(self):
        """Generate a shared secret for registration."""
        shared_secret = self.charm_config.get("shared-secret")
        saved_shared_secret = self.kv.get("shared-secret")
        if not shared_secret:
            if saved_shared_secret:
                return saved_shared_secret
            else:
                shared_secret = self.random_string(16)
                self.kv.set("shared-secret", shared_secret)
        return shared_secret

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
        host.service("restart", self.synapse_service)
        return True

    def restart(self):
        """Restart services."""
        self.restart_synapse()
        return True

    def start_service(self, service):
        """Start and enable the provided service, return run state."""
        host.service("start", service)
        host.service("enable", service)
        return host.service_running(service)

    def start_synapse(self):
        """Start and enable synapse."""
        synapse_running = self.start_service(self.synapse_service)
        return synapse_running

    def start_services(self):
        """Configure and start services."""
        synapse_result = self.start_synapse()
        return synapse_result

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
        if self.external_port == 8008:
            return "http://{}:8008".format(server_name)
        elif tls:
            return "https://{}".format(server_name)
        return "http://{}".format(server_name)

    def get_federation(self):
        """Get federation state."""
        return self.charm_config["enable-federation"]

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

    def remove_proxy_config(self):
        """Clean up proxy config and set exernal port back to 8008."""
        self.external_port = 8008

    def configure_proxy(self, proxy):
        """Configure Synapse for operation behind a reverse proxy."""
        server_name = self.get_server_name()
        tls_enabled = self.get_tls()
        federation_enabled = self.get_federation()

        if tls_enabled:
            self.external_port = 443
        else:
            self.external_port = 80

        internal_host = socket.getfqdn()
        proxy_config = [
            {
                "mode": "http",
                "external_port": self.external_port,
                "internal_host": internal_host,
                "internal_port": 8008,
                "subdomain": server_name,
            },
        ]

        if federation_enabled:
            proxy_config.append({
                "mode": "tcp",
                "external_port": 8448,
                "internal_host": internal_host,
                "internal_port": 8448,
                "subdomain": server_name,
            })

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
            "Rendering synapse configuration to {}".format(self.synapse_config),
            hookenv.DEBUG,
        )
        if self.pgsql_configured():
            templating.render(
                "homeserver.yaml.j2",
                self.synapse_config,
                {
                    "conf_dir": self.synapse_conf_dir,
                    "signing_key": self.get_synapse_signing_key(),
                    "registration_shared_secret": self.get_shared_secret(),
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
                    "enable_federation": self.charm_config["enable-federation"],
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
        if any_file_changed([self.synapse_config]):
            self.restart_synapse()
            return True
        return False

    def render_configs(self):
        """Render configuration for the homeserver and enabled bridges."""
        self.render_synapse_config()

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
        if not self.check_snap_installed(self.synapse_snap):
            hookenv.log("Installing {} snap".format(self.synapse_snap), hookenv.DEBUG)
            synapse_result = self.install_snap(self.synapse_snap)
        return synapse_result

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
                hookenv.open_port(8008)
                return True
            else:
                hookenv.status_set("blocked", "Matrix services are not running.")
        else:
            hookenv.status_set(
                "blocked",
                "Snaps are not installable. Check snap store accessibility or that resources are uploaded.",
            )
        hookenv.close_port(8008)
        return False
