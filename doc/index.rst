Python-pushover documentation
=============================

.. include:: ../README.rst
    :end-line: -7

API documentation
-----------------

.. automodule:: pushover
    :members:
    :undoc-members:
    :show-inheritance:


Command line
-------------

The module can also be called from the command line for basic message sending.
The minimum invocation is:

.. code-block:: bash
    
    python pushover.py --token <app-token> --client <client-id> "Hello!"


