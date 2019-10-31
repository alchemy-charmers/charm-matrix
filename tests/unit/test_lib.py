#!/usr/bin/python3


def test_pytest():
    assert True


def test_matrix_fixture(matrix):
    """ See if the helper fixture works to load charm configs """
    assert isinstance(matrix.charm_config, dict)


# test template generation when tls unset

# test template generation when tls set

# test snap install for irc when set true

# test snap install for slack when set true

# test snap removal for irc when set false

# test snap removal for slack when set false


# Include tests for functions in lib_layer_matrix
