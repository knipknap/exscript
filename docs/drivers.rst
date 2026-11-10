Drivers and OS Detection
========================

Devices differ in their prompts, their error messages, their login, and in
the commands that make a session suitable for scripts, such as turning
off the pager. A *driver* holds this knowledge for one operating system.
Exscript chooses the driver while it connects and logs in, or uses the
one that you choose.

Choosing a driver
-----------------

If you know the operating system, for example from an inventory, pass the
name of its driver. This is more reliable than a guess::

    from Exscript.protocols import SSH2

    conn = SSH2(driver='ios_xr')
    conn.set_driver('ios_xr')  # the same, also after the login

``set_driver(None)`` turns the guessing back on. A name that does not
exist raises a ``TypeError``, in the constructor as in ``set_driver()``,
so a typo, e.g. in an inventory, shows at once.

For :class:`~Exscript.Host` objects, set the option ``driver``; the
command line tool has ``--use-driver``::

    host.set_option('driver', 'ios_xr')

Without a driver, Exscript guesses. ``conn.guess_os()`` returns the name
of the guessed driver, and ``conn.get_driver()`` the driver in use.

The drivers
-----------

.. include:: _generated/drivers.inc

How the guess works
-------------------

Each driver rates what the device sends with a confidence between 0 (no
sign of its system) and 100 (certain):

- the SSH version string, for example ``SSH-2.0-Cisco-1.25``
  (``check_protocol_for_os()``);
- everything up to the end of the login, that is the banner and the
  prompts (``check_head_for_os()``);
- everything received, mostly to recognize the prompt
  (``check_response_for_os()``); after the login, only until a driver has
  a confidence of 80 or more;
- for NETCONF, the capabilities in the ``<hello>``
  (``netconf_capabilities_re``).

The driver with the highest confidence wins, and Exscript switches to a
better driver as soon as the data shows it. If no driver recognizes the
device, the guess is ``unknown``, and the ``generic`` driver is used: its
patterns work with the prompts and error messages of most devices.

Signals that several systems show, such as a ``Last login`` line or a
``router1 login:`` prompt, do not select a driver. A CI job measures the
accuracy of the guess on a corpus of device banners and recorded
sessions (``tools/osguess_report.py``).

If Exscript picks the wrong driver for a device, set the driver, and
please `report it
<https://github.com/knipknap/exscript/issues/new?template=device_support.yml>`_
with the login transcript. To see what the guess was based on, connect
with ``debug=3`` and enable Python's logging::

    import logging

    logging.basicConfig(level=logging.DEBUG)
    conn = SSH2(debug=3)

Writing a driver
----------------

A driver is a subclass of :class:`~Exscript.protocols.drivers.driver.Driver`
that changes what differs from the generic driver. Register it with
:func:`~Exscript.protocols.drivers.add_driver`; connections that are
created afterwards can then guess it, and accept its name::

    import re

    from Exscript.protocols.drivers import Driver, add_driver

    class AcmeDriver(Driver):
        def __init__(self):
            Driver.__init__(self, 'acme')
            self.prompt_re = [re.compile(r'[\r\n]acme-[\w-]+[>#] ?$')]

        def check_head_for_os(self, string):
            if 'Acme Networks OS' in string:
                return 90
            return 0

        def init_terminal(self, conn):
            conn.execute('terminal length 0')

    add_driver(AcmeDriver)

For the command line tool, put the class into a file without the call of
``add_driver()``, and pass the file with ``--load-driver``; the tool
registers every driver class in it.

A driver can set these attributes in its constructor:

``user_re``, ``password_re``
    Lists of patterns for the login prompts.

``prompt_re``
    Patterns for the command prompt. ``execute()`` waits until one of
    them matches at the end of the received data.

``error_re``
    Patterns for lines in a response that mean that the command failed;
    ``execute()`` then raises
    :class:`~Exscript.protocols.exception.InvalidCommandException`.

``login_error_re``
    Patterns for messages that mean that the login failed.

``reconnect_between_auth_methods``
    ``True`` for devices that close the SSH connection after an
    authentication method failed.

``netconf_capabilities_re``, ``netconf_device_params``
    Patterns for the NETCONF capabilities of the system, and the
    parameters of the ncclient device handler (:doc:`netconf`).

And it can override these methods:

``check_protocol_for_os()``, ``check_head_for_os()``, ``check_response_for_os()``
    Return the confidence for the given text, see above. Return 90 or
    more only for text that only this system shows, such as a vendor
    name, and less than 50 for signs that other systems may show, too.

``init_terminal(conn)``
    Prepares the session for scripts, for example by turning off the
    pager. ``conn.autoinit()`` calls it; :func:`Exscript.util.start.start`
    and the queue call ``autoinit()`` after the login.

``auto_authorize(conn, account, flush, bailout)``
    Gets the privileges that the commands need, for example with
    ``enable`` on IOS. ``login()`` calls it through
    ``conn.auto_app_authorize()`` after the authentication.

``logout(conn)``
    Ends the session; ``close()`` calls it. The default sends ``exit``.

``clean_response_for_re_match(response)``
    Removes what would keep the prompt patterns from matching, such as
    terminal control sequences that the device sends around the prompt.

The built-in drivers in ``src/Exscript/protocols/drivers`` are examples for
all of these. To contribute a driver, see :doc:`contributing`.
