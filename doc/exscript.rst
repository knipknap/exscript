Command Line Options
====================

Overview
--------

You can pass parameters (or lists of parameters) into the templates and
use them to drive what happens on the remote host. Exscript easily
supports logging, authentication mechanisms such as TACACS and takes
care of synchronizing the login procedure between multiple running
connections.

These features are enabled using simple command line options. The
following options are currently provided:

::

    Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      --account-pool=FILE   Reads the user/password combination from the given
                            file instead of prompting on the command line. The
                            file may also contain more than one user/password
                            combination, in which case the accounts are used round
                            robin.
      -c NUM, --connections=NUM
                            Maximum number of concurrent connections. NUM is a
                            number between 1 and 20, default is 1.
      --csv-hosts=FILE      Loads a list of hostnames and definitions from the
                            given file. The first line of the file must have the
                            column headers in the following syntax: "hostname
                            [variable] [variable] ...", where the fields are
                            separated by tabs, "hostname" is the keyword
                            "hostname" and "variable" is a unique name under which
                            the column is accessed in the script. The following
                            lines contain the hostname in the first column, and
                            the values of the variables in the following columns.
      -d PAIR, --define=PAIR
                            Defines a variable that is passed to the script. PAIR
                            has the following syntax: STRING=STRING.
      --default-domain=STRING
                            The IP domain name that is used if a given hostname
                            has no domain appended.
      --delete-logs         Delete logs of successful operations when done.
      -e EXSCRIPT, --execute=EXSCRIPT
                            Interprets the given string as the script.
      --hosts=FILE          Loads a list of hostnames from the given file (one
                            host per line).
      -i, --non-interactive
                            Do not ask for a username or password.
      -l DIR, --logdir=DIR  Logs any communication into the directory with the
                            given name. Each filename consists of the hostname
                            with "_log" appended. Errors are written to a separate
                            file, where the filename consists of the hostname with
                            ".log.error" appended.
      --no-echo             Turns off the echo, such that the network activity is
                            no longer written to stdout. This is already the
                            default behavior if the -c option was given with a
                            number greater than 1.
      -n, --no-authentication
                            When given, the authentication procedure is skipped.
                            Implies -i.
      --no-auto-logout      Do not attempt to execute the exit or quit command at
                            the end of a script.
      --no-prompt           Do not wait for a prompt anywhere. Note that this will
                            also cause Exscript to disable commands that require a
                            prompt, such as "extract".
      --no-initial-prompt   Do not wait for a prompt after sending the password.
      --no-strip            Do not strip the first line of each response.
      --overwrite-logs      Instructs Exscript to overwrite existing logfiles. The
                            default is to append the output if a log already
                            exists.
      -p STRING, --protocol=STRING
                            Specify which protocol to use to connect to the remote
                            host. Allowed values for STRING include: dummy,
                            pseudo, ssh, ssh1, ssh2, telnet. The default protocol
                            is telnet.
      --retry=NUM           Defines the number of retries per host on failure.
                            Default is 0.
      --retry-login=NUM     Defines the number of retries per host on login
                            failure. Default is 0.
      --sleep=TIME          Waits for the specified time before running the
                            script. TIME is a timespec as specified by the 'sleep'
                            Unix command.
      --ssh-auto-verify     Automatically confirms the 'Host key changed' SSH
                            error  message with 'yes'. Highly insecure and not
                            recommended.
      --ssh-key=FILE        Specify a key file that is passed to the SSH client.
                            This is equivalent to using the "-i" parameter of the
                            openssh command line client.
      -v NUM, --verbose=NUM
                            Print out debug information about the network
                            activity. NUM is a number between 0 (min) and 5 (max).
                            Default is 1.
      -V NUM, --parser-verbose=NUM
                            Print out debug information about the Exscript
                            template parser. NUM is a number between 0 (min) and 5
                            (max). Default is 0.

Using Account Pooling
---------------------

It is possible to provide an account pool from which Exscript takes a
user account whenever it needs to log into a remote host. Depending on
the authentification mechanism used in your network, you may
significantly increase the speed of parallel connections by using more
than one account in parallel. The following steps need to be taken to
use the feature:

#. Create a file with the following format::

       [account-pool]
       user=password
       other_user=another_password
       somebody=yet_another_password

   Note that the password needs to be base64 encrypted, just putting
   plain passwords there will NOT work.

#. Save the file. It is assumed that you are aware of the security
   implications of saving your login passwords in a text file.

#. Start Exscript with the ``–account-pool FILE`` option. For example::

       exscript --account-pool /home/user/my_accounts my.exscript host4

Using a CSV file as input
-------------------------

By providing the –csv-hosts option you may pass a list of hosts to
Exscript while at the same time providing a number of variables to the
script. The CSV file should have the following format::

    hostname my_variable another_variable
    myhost value another_value
    yourhost hello world

Note that fields are separated using the tab character, and the first
line must start with the string “hostname” and is followed by a list of
column names.

In the Exscript, you may then access the variables using those column
names::

    ls -l $my_variable
    touch $another_variable
