from charmhelpers.core import hookenv

# TODO: limits.conf file handle config
# TODO: template configuration
# TODO: handle reverse proxy relation
# TODO: handle DB relation
# TODO: handle apt sources and key
# TODO: handle package install
# TODO: handle federation bridges install
# TODO: libjemalloc


class MatrixHelper:
    def __init__(self):
        self.charm_config = hookenv.config()

    def set_password(self):
        """ An example function for calling from an action """
        return

    def register_user(self, user, password=None, admin=False):
        """Create a user with the provided credentials, and optionally set as an admin."""
        return
