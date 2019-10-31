"""Matrix helper class for reactive charm layer."""
from lib_layer_matrix import MatrixHelper
from charmhelpers.core import hookenv
from charms.reactive import set_flag, when_not

matrix = MatrixHelper()


@when_not("matrix.installed")
def install_matrix():
    # Do your setup here.
    #
    # If your charm has other dependencies before it can install,
    # add those as @when() clauses above., or as additional @when()
    # decorated handlers below
    #
    # See the following for information about reactive charms:
    #
    #  * https://jujucharms.com/docs/devel/developer-getting-started
    #  * https://github.com/juju-solutions/layer-basic#overview
    #
    hookenv.status_set("active", "")
    set_flag("matrix.installed")
