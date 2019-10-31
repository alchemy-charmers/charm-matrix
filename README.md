[![pipeline status](https://git.ec0.io/pirate-charmers/charm-matrix/badges/master/pipeline.svg)](https://git.ec0.io/pirate-charmers/charm-matrix/commits/master)                                                                  
[![coverage report](https://git.ec0.io/pirate-charmers/charm-matrix/badges/master/coverage.svg)](https://git.ec0.io/pirate-charmers/charm-matrix/commits/master)

Matrix
======

This charm will deploy a Matrix homeserver, running synapse, and optionally supporting the following bridges -
* matrix-appservice-irc
* matrix-appservice-slack

Deployment
==========

This charm currently relies on the following snaps being built locally and then deployed as resources:
* [snap-matrix-synapse - merged upstream](https://github.com/matrix-org/matrix-synapse)
* [snap-matrix-appservice-irc - in review](https://github.com/matrix-org/matrix-appservice-irc/pull/807)
* [snap-matrix-appservice-slack - in review](https://github.com/matrix-org/matrix-appservice-slack/pull/231)

None of these charms are currently published to to store, pending further discussions upstream.
In the meantime, layer-snap provides the ability to upload the built charms as resources, where they will be deployed locally.

Configuration
=============

This charm supports a number of configuration items for customising the behaviour of the homeserver.
These are documented in the `config.yaml` file, however the following are the most important:

`enable-registration` controls whether or not public users can register an account.
`server-name` controls the FQDN of the server used in federation and other client operations.
`shared-secret` allows you to provide a shared secret which is used when registering users, if enabled.
`enable-irc` installs and configures the IRC bridge when set to true.
`enable-slack` installs and configures the Slack bridge when set to true.

Do ensure you review the remainder of the configuration items, as they control security and privacy related aspects of Synapse, and the
defaults might not suit your needs, erring on the side of privacy.

Author
======

This charm and the related snap work has been written by [James Hebden](mailto:james+matrix@ec0.io) of the Pirate Charmers group.

Primary development is done on the [Pirate Charmers GitLab](https://git.ec0.io/pirate-charmers), and mirrored to [GitHub](https://github.com/pirate-charmers).
