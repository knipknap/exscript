#
# Copyright (C) 2007-2010 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
The command line tools ``exscript`` and ``otp``.

The package installs both as commands, and ``python -m Exscript`` runs
``exscript``, too. ``exscript`` runs a template on hosts; see the
:doc:`/cli_tutorial` and ``exscript --help``. ``otp`` asks for a password,
and prints the S/Key one-time password for a sequence number and a salt.
"""

import argparse
import ast
import getpass
import importlib.util
import os
import re
import signal
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from types import FrameType
from typing import NoReturn

import Exscript.protocols.drivers
from Exscript import Account, Host, PrivateKey, Queue, __version__
from Exscript.logger import setupLogging
from Exscript.protocols import Protocol, protocol_map
from Exscript.util import template
from Exscript.util.cast import to_host
from Exscript.util.crypt import otp
from Exscript.util.decorator import autologin
from Exscript.util.file import (
    get_accounts_from_file,
    get_hosts_from_csv,
    get_hosts_from_file,
    load_lib,
)
from Exscript.util.interact import get_login
from Exscript.util.log import log_to_file
from Exscript.workqueue.job import Thread

_bracket_expression = r"\{([^\]]*)\}"
_define_expression = rf"^\S+=(?:\S+|{_bracket_expression})$"
_bracket_expression_re = re.compile(rf"^{_bracket_expression}$")
_define_expression_re = re.compile(_define_expression)
_duration_re = re.compile(r"(\d+(?:\.\d*)?|\.\d+)([smhd]?)")
_duration_units = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}


def _duration(text: str) -> float:
    """
    Returns the seconds of a time like the sleep command takes it, e.g. "1h 30m":
    numbers with an optional suffix s, m, h or d, separated by blanks.
    Raises a ValueError for other text.

    :type  text: str
    :param text: The time.
    :rtype:  float
    :return: The time in seconds.
    """
    seconds = 0.0
    for part in text.split():
        match = _duration_re.fullmatch(part)
        if match is None:
            raise ValueError(part)
        seconds += float(match.group(1)) * _duration_units[match.group(2)]
    return seconds


# argparse names the type in its errors: "invalid duration value: 'x'".
_duration.__name__ = "duration"


def _expand_bracket(value_name: str, value: str) -> object:
    """
    Returns the given value of the variable with the given name, or, if the
    value is a prompt in braces, asks the user for the value and returns
    that. ``{PROMPT}`` reads a line, ``{!PROMPT}`` a password, ``{#PROMPT}``
    a Python literal such as a number or a list (or the line as it is, if it
    is no literal), and ``{}`` asks for a value for the variable.

    :type  value_name: str
    :param value_name: The name of the variable.
    :type  value: str
    :param value: The value, or a prompt in braces.
    :rtype:  object
    :return: The value.
    """
    match = _bracket_expression_re.match(value)
    if match is None:
        return value
    prompt = match.group(1) or f"a value for '{value_name}' "
    if prompt.startswith("!"):
        value = getpass.getpass(f"Please enter {prompt.lstrip('!')}: ")
    else:
        value = input(f"Please enter {prompt.lstrip('#')}: ")
        if prompt.startswith("#"):
            try:
                value = ast.literal_eval(value)
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                pass
    return value


def _expand_host_variables(host: Host) -> None:
    """
    Asks the user for the values of the variables of the given host that are
    prompts in braces, also in lists, and replaces the prompts by the
    values; see :func:`_expand_bracket`.

    :type  host: Host
    :param host: The host.
    """
    # Define host-specific variables.
    for key, value in list(host.get_all().items()):
        if isinstance(value, str):
            value = _expand_bracket(key, value)
        elif hasattr(value, "__iter__"):
            for n in range(len(value)):
                if not isinstance(value[n], str):
                    continue
                value[n] = _expand_bracket(key, value[n])
        host.set(key, value)


def _exit_on_sigint(signum: int, frame: FrameType | None) -> NoReturn:
    """
    The handler of SIGINT (Ctrl+C) while the template runs: writes
    "Interrupted." to stderr, and ends the process at once with exit status
    130. A KeyboardInterrupt would end it only after the threads of the
    running connections, which cannot be interrupted.
    """
    try:
        sys.stdout.flush()
        sys.stderr.write('Interrupted.\n')
        sys.stderr.flush()
    finally:
        os._exit(130)


def _join(queue: Queue) -> None:
    """
    Waits until the given queue has completed all jobs, like queue.join(),
    but in short slices, so that the main thread handles Ctrl+C meanwhile:
    on Windows, Ctrl+C does not interrupt a blocking wait for a lock before
    Python 3.14.
    """
    while not queue.is_completed():
        time.sleep(0.2)
    queue.join()


def _run(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """
    Runs the template on the hosts as the given command line arguments say,
    and returns the number of hosts on which it failed. Invalid arguments
    end the process through ``parser.error()``.

    :type  parser: argparse.ArgumentParser
    :param parser: The parser of the arguments, see :func:`_create_parser`.
    :type  args: argparse.Namespace
    :param args: The parsed arguments.
    :rtype:  int
    :return: The number of failed actions.
    """

    def mkhost(name: str) -> Host:
        return to_host(
            name,
            default_protocol=args.protocol,
            default_domain=args.default_domain,
        )

    def mkhosts_from_file(filename: Path) -> list[Host]:
        return get_hosts_from_file(
            filename,
            default_protocol=args.protocol,
            default_domain=args.default_domain,
        )

    def mkhosts_from_csv(filename: Path) -> list[Host]:
        return get_hosts_from_csv(
            filename,
            default_protocol=args.protocol,
            default_domain=args.default_domain,
        )

    # Setup package logging.
    setupLogging(
        package=bool(args.verbose),
        parser=bool(args.parser_verbose),
        protocol=bool(args.protocol_verbose),
    )

    # Read the Exscript.
    script_extra_content = ""  # init for later use
    if args.execute:
        script_content = args.execute
    else:
        if not args.filename:
            parser.error("Missing template filename")
        try:
            with open(args.filename, encoding="utf-8") as fp:
                script_content = fp.read()
        except OSError as e:
            parser.error(str(e))

    # Extract the hostnames out of the command line arguments.
    if args.execute and args.filename:
        args.host = [args.filename] + args.host
    hosts = [mkhost(h) for h in args.host]

    # If a filename containing hostnames AND VARIABLES was given, read it.
    if args.csv_hosts:
        try:
            path = Path(os.path.expandvars(args.csv_hosts)).expanduser()
            csv_hosts = mkhosts_from_csv(path)
        except OSError as e:
            parser.error(str(e))
        if not csv_hosts:
            print(f"Warning: {args.csv_hosts} is empty.")
        hosts += csv_hosts

    # If a filename containing hostnames was given, read it.
    if args.hosts:
        try:
            path = Path(os.path.expandvars(args.hosts)).expanduser()
            txt_hosts = mkhosts_from_file(path)
        except OSError as e:
            parser.error(str(e))
        except ValueError as e:
            parser.error(str(e))
        if not txt_hosts:
            print(f"Warning: {args.hosts} is empty.")
        hosts += txt_hosts

    # If a filename of an Exscript driver was given, import it.
    if args.load_driver:
        path = Path(os.path.expandvars(args.load_driver)).expanduser()
        print(f"Searching drivers in {args.load_driver}...")
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"{path} is not a Python file")
            driver_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(driver_module)
        except OSError as e:
            parser.error(str(e))
        except Exception:
            sys.stderr.write(f"Error in driver {args.load_driver}\n")
            raise
        for name, obj in list(driver_module.__dict__.items()):
            if Exscript.protocols.drivers.isdriver(obj):
                Exscript.protocols.drivers.add_driver(obj)
                print(f"Driver {repr(name)} added.")

    # Make sure that all mandatory options are present.
    if not hosts:
        parser.error("No hosts to connect to")

    # Set host options.
    for host in hosts:
        host.set_option("debug", args.protocol_verbose)
        if args.ssh_disabled_algs:
            ssh_disabled_algs = {}
            for algs_map in args.ssh_disabled_algs.split(";"):
                key, algs = algs_map.split("=", maxsplit=1)
                ssh_disabled_algs[key] = algs.split(",")
            host.set_option("disabled_algorithms", ssh_disabled_algs)
        if args.ssh_preferred_auth:
            host.set_option("preferred_authentications", args.ssh_preferred_auth.split(","))
        host.set_option("verify_fingerprint", not args.ssh_auto_verify)
        host.set_option("host_key_policy", args.ssh_host_key_policy)

    # Prepare the code that is executed after the user script has completed.
    if not args.no_auto_logout:
        script_extra_content += r"""
    ## Exscript generated commands. ##
    {connection.close()}"""

    # Load extra functions.
    functions = {}
    if args.lib:
        try:
            functions = load_lib(args.lib)
        except OSError as e:
            parser.error(str(e))

    # Test whether the template compiles.
    template.debug = args.parser_verbose
    vars = functions.copy()
    vars.update(args.define)
    if args.filename:
        vars["__filename__"] = args.filename
    vars.update(hosts[0].get_all())
    try:
        template.test(script_content, secure=not args.insecure, **vars)
        template.test(script_extra_content, secure=not args.insecure, **vars)
    except Exception as e:
        if args.parser_verbose > 0:
            raise
        parser.error(str(e))
    script_content += script_extra_content
    # NOTE: Disable debugging again until Parser logging is more than just dumping!
    template.debug = 0

    # Create Exscript.
    queue = Queue(
        domain=args.default_domain,
        host_driver=args.use_driver,
        verbose=args.verbose,
        max_threads=args.connections,
    )
    default_pool = queue.account_manager.default_pool

    # Read the account pool file.
    try:
        if args.account_pool:
            path = Path(os.path.expandvars(args.account_pool)).expanduser()
            accounts = get_accounts_from_file(path)
            default_pool.add_account(accounts)
    except OSError as e:
        parser.error(str(e))
    if args.account_pool and default_pool.n_accounts() == 0:
        print(f"WARNING: No accounts found in account pool file ({args.account_pool})!")

    # Read username and password.
    if args.non_interactive or default_pool.n_accounts() > 0:
        user = None
        password = None
        password2 = None
    else:
        try:
            user, password = get_login()
        except KeyboardInterrupt:
            sys.exit(1)
        if args.authorization:
            prompt = "Please enter your authorization password: "
            password2 = getpass.getpass(prompt)
        else:
            password2 = password

    # Read the SSH key.
    if args.ssh_key:
        print(f"Reading key from {args.ssh_key}")
        try:
            key = PrivateKey.from_file(args.ssh_key, password)
        except ValueError as e:
            parser.error(str(e))
        if user is None:
            try:
                user = getpass.getuser()
            except (KeyError, OSError):  # no user name: OSError since Python 3.13
                user = None
    else:
        key = None

    # Add the account to the pool.
    if user is not None:
        account = Account(user, password, password2, key=key)
        default_pool.add_account(account)

    # Ask for values of marked variables.
    for host in hosts:
        _expand_host_variables(host)
    for key, val in list(args.define.items()):
        args.define[key] = _expand_bracket(key, val)

    # Choose the template processing type.
    tmpl_vars = args.define
    if args.no_prompt:

        def function(job: Thread, host: Host, conn: Protocol, **kwargs: object) -> object:
            kwargs.update(functions)
            kwargs.update(tmpl_vars)
            if args.filename:
                kwargs["__filename__"] = args.filename
            kwargs.update(host.get_all())
            return template.paste(
                conn, script_content, args.no_escaping, secure=not args.insecure, **kwargs
            )

    else:

        def function(job: Thread, host: Host, conn: Protocol, **kwargs: object) -> object:
            kwargs.update(functions)
            kwargs.update(tmpl_vars)
            if args.filename:
                kwargs["__filename__"] = args.filename
            kwargs.update(host.get_all())
            return template.eval(
                conn,
                script_content,
                not args.no_strip,
                args.no_escaping,
                secure=not args.insecure,
                **kwargs,
            )

    # Wrap the template processor such that the login procedure is automated.
    if not args.no_authentication:
        attempts = args.retry_login + 1
        decorator = autologin(attempts=attempts)
        function = decorator(function)

    # Wrap the template processor such that logging is enabled.
    if args.logdir:
        # Create the log directory.
        if not os.path.exists(args.logdir):
            print(f"Creating log directory ({args.logdir})...")
            try:
                os.makedirs(args.logdir)
            except OSError as e:
                parser.error(str(e))

        # Enable logging.
        mode = args.overwrite_logs and "w" or "a"
        decorator = log_to_file(args.logdir, mode, args.delete_logs)
        function = decorator(function)

    # Ctrl+C ends the process at once from here on, see _exit_on_sigint().
    # Not before: while getpass() reads a password, the terminal does not
    # echo, and only a KeyboardInterrupt lets getpass() turn the echo on again.
    sigint_handler = signal.signal(signal.SIGINT, _exit_on_sigint)
    try:
        # Wait until the specified time.
        if args.sleep:
            print(f"Waiting for {args.sleep:g} seconds...", end="", flush=True)
            time.sleep(args.sleep)
            print("time expired, starting script.")

        # Run the template.
        queue.run(hosts, function, attempts=args.retry + 1)
        _join(queue)
    finally:
        signal.signal(signal.SIGINT, sigint_handler)
    failed = queue.failed
    queue.destroy(force=True)
    return failed


# Define command line option value types.
def _assignment(value: str, pattern: re.Pattern[str] = _define_expression_re) -> str:
    """
    Checks a value of the option -d/--define: returns it if it matches the
    given pattern, by default that of an assignment NAME=VALUE, and raises
    an ArgumentTypeError if not.

    :type  value: str
    :param value: The value of the option.
    :type  pattern: re.Pattern
    :param pattern: The pattern of valid values.
    :rtype:  str
    :return: The value.
    """
    if not pattern.match(value):
        raise argparse.ArgumentTypeError(f"invalid value: {value}")
    return value


class _DefineAction(argparse.Action):
    """
    The action of the option -d/--define: stores the variables of the given
    assignments NAME=VALUE in the dictionary of the option. Variables in
    double underscores, such as ``__filename__``, are internal.
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[str] | None,
        option_string: str | None = None,
    ) -> None:
        """
        Adds the variables of the given assignments to the dictionary of the
        option in the given namespace, or reports an error through the parser
        if a variable is internal.
        """
        if type(values) == str:
            values = [values]
        d = getattr(namespace, self.dest)
        for value in values or ():
            left, right = value.split("=")
            if left.startswith('__') and left.endswith('__'):
                parser.error('Assignment to internal variable %s' % repr(left))
            d[left] = right
        setattr(namespace, self.dest, d)


def _create_parser() -> argparse.ArgumentParser:
    """
    Returns a parser of the command line arguments of ``exscript``.

    :rtype:  argparse.ArgumentParser
    :return: The parser.
    """
    parser = argparse.ArgumentParser(
        prog="exscript", epilog="\N{COPYRIGHT SIGN} 2007-2023 by Samuel Abels."
    )

    parser.add_argument("--version", action="version", version=__version__)

    parser.add_argument(
        "filename",
        default=None,
        nargs="?",
        help="""
Filename of the template to be executed. Ignored with
"-e/--execute" and taken as first positional host.
""".strip(),
    )

    parser.add_argument(
        "host",
        default=list(),
        nargs="*",
        help="""
List of hostnames.
""".strip(),
    )

    parser.add_argument(
        "--account-pool",
        default=None,
        metavar="FILE",
        help="""
Reads the user/password combination from the given file
instead of prompting on the command line. The file may
also contain more than one user/password combination, in
which case the accounts are used round robin.
""".strip(),
    )

    parser.add_argument(
        "-c",
        "--connections",
        type=int,
        metavar="NUM",
        default=1,
        help="""
Maximum number of concurrent connections.
NUM is a number between 1 and 20, default is 1.
""".strip(),
    )

    parser.add_argument(
        "--csv-hosts",
        default=None,
        metavar="FILE",
        help="""
Loads a list of hostnames and definitions from the given file.
The first line of the file must have the column headers in the
following syntax: "hostname [variable] [variable] ...", where
the fields are separated by tabs, "hostname" is the keyword
"hostname" and "variable" is a unique name under which the
column is accessed in the script.
The following lines contain the hostname in the first column,
and the values of the variables in the following columns.
""".strip(),
    )

    parser.add_argument(
        "-d",
        "--define",
        type=_assignment,
        action=_DefineAction,
        default=dict(),
        metavar="PAIR",
        help="""
Defines a variable that is passed to the script.
PAIR has the following syntax: STRING=STRING.
Use a prompt with the following syntax: VAR={"PROMPT"}.
Use a password prompt with the following syntax: VAR={\\!"PROMPT"}.
Evaluate the value of a prompt as a Python literal (e.g. a number or a list)
with the following syntax: VAR={#"PROMPT"}.
""".strip(),
    )

    parser.add_argument(
        "--default-domain",
        metavar="STRING",
        default="",
        help="""
The IP domain name that is used if a given hostname has no domain appended.
""".strip(),
    )

    parser.add_argument(
        "--delete-logs",
        action="store_true",
        default=False,
        help="Delete logs of successful operations when done.",
    )

    parser.add_argument(
        "--no-escaping",
        action="store_true",
        default=False,
        help="""
Disable additional evaluation of escaped control characters (NUL/BEL/BS/ESC/FF/VT),
octal (\\ooo), hexadecimal (\\xhh) and unicode (\\uhhhh, \\Uhhhhhhhh) characters
in the script. Evaluation of escaped CR, LF and TAB characters in strings is always
enabled. This is irrelevant for RPC bodies in Netconf as XML does not support
escaping (see XML entity syntax instead).
""".strip(),
    )

    parser.add_argument(
        "--lib",
        default=None,
        metavar="FILE",
        help="""
A python file containing a __lib__ dictionary that points to extra
functions to be made available in the Exscript template.
""".strip(),
    )

    parser.add_argument(
        "--insecure",
        action="store_true",
        default=False,
        help="""
Allow the template to call the functions that run local commands or access
local files: sys.exec, sys.env and file.* (except file.exists).
""".strip(),
    )

    parser.add_argument(
        "--load-driver",
        default=None,
        metavar="FILE",
        help="""
A python file containing an Exscript driver class.
""".strip(),
    )

    parser.add_argument(
        "--use-driver",
        default=None,
        metavar="NAME",
        help="""
The name of an exscript driver to use for all connections (overriding os detection).
""".strip(),
    )

    parser.add_argument(
        "-e",
        "--execute",
        default=None,
        metavar="EXSCRIPT",
        help="""
Interprets the given string as the script.
""".strip(),
    )

    parser.add_argument(
        "--hosts",
        default=None,
        metavar="FILE",
        help="""
Loads a list of hostnames from the given file (one host per line).
""".strip(),
    )

    parser.add_argument(
        "-i",
        "--non-interactive",
        action="store_true",
        default=False,
        help="""
Do not ask for a username or password, but still try to authenticate.
May be used if the login credentials are passed as part of a URI formatted
hostname.
""".strip(),
    )

    parser.add_argument(
        "-l",
        "--logdir",
        default=None,
        metavar="DIR",
        help="""
Logs any communication into the directory with the given name.
Each filename consists of the hostname with ".log" appended.
Errors are written to a separate file, where the filename
consists of the hostname with ".log.error" appended.
""".strip(),
    )

    parser.add_argument(
        "-n",
        "--no-authentication",
        action="store_true",
        default=False,
        help="""
When given, the automatic authentication procedure is skipped. Implies -i.
""".strip(),
    )

    parser.add_argument(
        "--authorization",
        action="store_true",
        default=False,
        help="""
Ask for an authorization password in addition to the authentication password.
""".strip(),
    )

    parser.add_argument(
        "--no-auto-logout",
        action="store_true",
        default=False,
        help="""
Do not attempt to execute the exit or quit command at the end of a script.
""".strip(),
    )

    parser.add_argument(
        "--no-prompt",
        action="store_true",
        default=False,
        help="""
Do not wait for a prompt anywhere (except during the authentication
procedure). Note that this will also cause Exscript to disable commands
that require a prompt, such as "extract".
""".strip(),
    )

    parser.add_argument(
        "--no-strip",
        action="store_true",
        default=False,
        help="""
Do not strip the command echo from each response. This is irrelevant for RPC
bodies as Netconf does not echo commands.
""".strip(),
    )

    parser.add_argument(
        "--overwrite-logs",
        action="store_true",
        default=False,
        help="""
Instructs Exscript to overwrite existing logfiles. The default
is to append the output if a log already exists.
""".strip(),
    )

    protocols = list(protocol_map.keys())
    protocols.sort()
    parser.add_argument(
        "-p",
        "--protocol",
        metavar="STRING",
        default="ssh",
        choices=protocols,
        help=f"""
Specify which protocol to use to connect to the remote host.
Allowed values for STRING include: {", ".join(protocols)}.
The default protocol is ssh.
""".strip(),
    )

    parser.add_argument(
        "--retry",
        type=int,
        metavar="NUM",
        default=0,
        help="""
Defines the number of retries per host on failure. Default is 0.
""".strip(),
    )

    parser.add_argument(
        "--retry-login",
        type=int,
        metavar="NUM",
        default=0,
        help="""
Defines the number of retries per host on login failure. Default is 0.
""".strip(),
    )

    parser.add_argument(
        "--sleep",
        metavar="TIME",
        type=_duration,
        default="",
        help="""
Waits for the specified time before running the script.
TIME is a number of seconds, optionally with the suffix m, h or d,
like for the 'sleep' Unix command; e.g. "90" or "1h 30m".
""".strip(),
    )

    parser.add_argument(
        "--ssh-auto-verify",
        action="store_true",
        default=False,
        help="""
Disables the verification of SSH host keys, so that any key is accepted.
Highly insecure and not recommended.
""".strip(),
    )

    parser.add_argument(
        "--ssh-host-key-policy",
        choices=("reject", "warn", "auto-add"),
        default="reject",
        help="""
What to do with SSH hosts that are not in ~/.ssh/known_hosts: reject the
connection (the default), warn and connect, or add the host key to
known_hosts and connect.
""".strip(),
    )

    parser.add_argument(
        "--ssh-disabled-algs",
        default="",
        metavar="STRING",
        help="""
Specify a mapping of disabled SSH algorithms according to Paramiko's
SSHClient/Transport constructor. The syntax on the CLI goes like this:
"ciphers=aes128-cbc,3des-cbc;pubkeys=ssh-rsa,ssh-dss". This will be
parsed into a mapping as expected by the Paramiko constructor. Please
refer to the "paramiko.Transport" documentation for details.
""".strip(),
    )

    parser.add_argument(
        "--ssh-preferred-auth",
        default="",
        metavar="STRING",
        help="""
Specify a comma-separated list of preferred SSH authentication
types in the preferred order. This is equivalent to the
"-o PreferredAuthentications" option of the openssh command
line client and the corresponding SSH config option.
The default is "publickey,keyboard-interactive,password" which
is derived from the SSH config default value.
""".strip(),
    )

    parser.add_argument(
        "--ssh-key",
        default=None,
        metavar="FILE",
        help="""
Specify a key file that is passed to the SSH client.
This is equivalent to using the "-i" parameter of the
openssh command line client.
""".strip(),
    )

    parser.add_argument(
        "-v",
        "--verbose",
        type=int,
        metavar="NUM",
        default=1,
        help="""
Print out debug information about the queue.
NUM is a number between 0 (min) and 5 (max). Default is 1.
""".strip(),
    )

    parser.add_argument(
        "-V",
        "--parser-verbose",
        type=int,
        metavar="NUM",
        default=0,
        help="""
Print out debug information about the Exscript template parser.
NUM is a number between 0 (min) and 5 (max). Default is 0.
""".strip(),
    )

    parser.add_argument(
        "--protocol-verbose",
        type=int,
        metavar="NUM",
        default=0,
        help="""
Print out debug information about the network activity.
NUM is a number between 0 (min) and 5 (max). Default is 0.
""".strip(),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Runs the command line tool ``exscript`` with the given arguments. Once
    the template runs, Ctrl+C ends the process at once with exit status 130,
    also while connections are running.

    :type  argv: list[str] | None
    :param argv: The arguments without the name of the program; by default
        those of the process.
    :rtype:  int
    :return: The exit status: 0 if the template succeeded on all hosts,
        else 1. Invalid arguments, ``--help`` and ``--version`` end the
        process through SystemExit, as usual with argparse.
    """
    parser = _create_parser()
    failed = _run(parser, parser.parse_args(argv))
    if failed != 0:
        print(f"error: {failed} actions failed.", file=sys.stderr)
        return 1
    return 0


def otp_main(argv: list[str] | None = None) -> int:
    """
    Runs the command line tool ``otp`` with the given arguments: asks for a
    password, and prints the S/Key one-time password for the given sequence
    number and salt; see :func:`Exscript.util.crypt.otp`.

    :type  argv: list[str] | None
    :param argv: The arguments without the name of the program; by default
        those of the process.
    :rtype:  int
    :return: The exit status, 0. Invalid arguments and ``--help`` end the
        process through SystemExit, as usual with argparse.
    """
    # Define the command line syntax.
    parser = argparse.ArgumentParser(prog='otp')
    parser.add_argument('sequence', help='the sequence number')
    parser.add_argument('salt', help='the salt value')
    args = parser.parse_args(argv)
    seq = args.sequence
    salt = args.salt

    try:
        seq = int(seq)
    except ValueError:
        parser.error('first argument must be a number')

    password = getpass.getpass('Password: ')
    print(otp(password, salt, seq))
    return 0
