Installation
============

Prerequisites
-------------

Exscript requires Python 3.12 or later and runs on Linux, macOS and Windows.
pip and uv install the other required packages, among them paramiko for SSH
and ncclient for NETCONF.

Installing with pip or uv
-------------------------

::

    pip install Exscript

or, in a project managed with uv::

    uv add Exscript

To trace sessions with OpenTelemetry, install the ``otel`` extra, e.g.
``pip install "Exscript[otel]"``.

For colored messages and a progress display in the command line tools
``exscript`` and ``otp``, install the ``cli`` extra, which adds rich, e.g.
``pip install "Exscript[cli]"``, or ``uv tool install "Exscript[cli]"`` for
the commands alone. The library itself does not need it.

Installing from GitHub
----------------------

::

    git clone https://github.com/knipknap/exscript
    cd exscript
    uv sync

Running the automated test suite
--------------------------------

In a checkout from GitHub, run the test suite with::

    uv run pytest

There shouldn\x27t be any errors, so if something comes up,
`please file a bug <https://github.com/knipknap/exscript/issues>`_.
