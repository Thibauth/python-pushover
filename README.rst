``python-pushover`` aims at providing comprehensive Python bindings for the API
of the `Pushover Notification Service`_ as documented here__.

.. _Pushover Notification Service: https://pushover.net/ 
.. __: https://pushover.net/api

Installation
------------

You can install python-pushover from Pypi_ with:

.. code-block:: bash

    $ pip install python-pushover

Or you can install it directly from GitHub_:

.. code-block:: bash

    git clone https://github.com/Thibauth/python-pushover.git
    cd python-pushover
    pip install .

.. _Pypi: https://pypi.python.org/pypi/python-pushover/
.. _GitHub: https://github.com/Thibauth/python-pushover

Overview
--------

After being imported, the module must be initialized by calling the ``init``
function with a valid application token. Thus, a typical use of the
``pushover`` module looks like this:

.. code-block:: python

    from pushover import init, Client

    init("<token>")
    Client("<user-key>").send_message("Hello!", title="Hello")

You can also pass the ``api_token`` optional argument to ``Client`` to
initialize the module at the same time:

.. code-block:: python

    from pushover import Client

    client = Client("<user-key>", api_token="<api-token>")
    client.send_message("Hello!", title="Hello")

Command line
~~~~~~~~~~~~

``python-pushover`` also comes with a command line utility ``pushover`` that
you can use as follows:

.. code-block:: bash

    pushover --api-token <api-token> --user-key <user-key> "Hello!"

Use ``pushover --help`` to see the list of available options.

Configuration
~~~~~~~~~~~~~

Both the ``pushover`` module and the ``pushover`` command line utility support
reading arguments from a configuration file.

The most basic configuration file looks like this:

.. code-block:: ini

    [Default]
    api_token=aaaaaa
    user_key=xxxxxx

You can have additional sections and specify a device as well:

.. code-block:: ini

    [Sam-iPhone]
    api_token=bbbbbb
    user_key=yyyyyy
    device=iPhone

``python-pushover`` will attempt to read the configuration from
``~/.pushoverrc`` by default. The section to read can be specified by using the
``profile`` argument. With the configuration file above, you can send a message
by simply doing:

.. code-block:: python

    from pushover import Client

    Client().send_message("Hello!", title="Hello")

or ``pushover --title "Hello" "Hello!"`` from the command line.

API
---

You can access the full API documentation here__.

.. __: http://pythonhosted.org/python-pushover/#module-pushover
