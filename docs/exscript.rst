Command Line Options
====================

Overview
--------

You can pass parameters (or lists of parameters) into the templates and
use them to drive what happens on the remote host. Exscript easily
supports logging, authentication mechanisms such as TACACS and takes
care of synchronizing the login procedure between multiple running
connections.

These features are enabled using command line options. ``exscript --help``
shows them:

.. literalinclude:: _generated/exscript-help.txt
   :language: text

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

   The passwords are base64 encoded; plain passwords do not work. Base64
   does not protect the passwords: anyone who can read the file can
   decode them.

#. Save the file. It is assumed that you are aware of the security
   implications of saving your login passwords in a text file.

#. Start Exscript with the ``--account-pool FILE`` option. For example::

       exscript --account-pool /home/user/my_accounts my.exscript host4

Using a CSV file as input
-------------------------

By providing the ``--csv-hosts`` option you may pass a list of hosts to
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
