Trouble Shooting
================

Common Pitfalls
---------------

Generally, the following kinds of errors that may happen at runtime:

#. **A script deadlocks.** In other words, Exscript sends no further
   commands even though the remote host is already waiting for a
   command. This generally happens when a prompt is not recognized.

#. **A script executes a command before the remote host is ready.** This
   happens when a prompt was detected where none was really included in
   the response.

#. **A script terminates before executing all commands.** This happens
   when two (or more) prompts were detected where only one was expected.

The following sections explain when these problems may happen and how to
fix them.

Deadlocks
---------

Exscript tries to automatically detect a prompt, so generally you
should not have to worry about prompt recognition. The following prompt
types are supported:

::

    [sam123@home ~]$
    sam@knip:~/Code/exscript$
    sam@MyHost-X123$
    MyHost-ABC-CDE123$
    MyHost-A1$
    MyHost-A1(config)$
    FA/0/1/2/3$
    FA/0/1/2/3(config)$
    admin@s-x-a6.a.bc.de.fg:/$

Note: The trailing "$" may also be any of the following characters:
"$#>%"

However, in some rare cases, a remote host may have a prompt that
Exscript can not recognize. Similarly, in some scripts you might want
to execute a special command that triggers a response that does not
include a prompt Exscript can recognize.

In both cases, the solution includes defining the prompt manually, such
that Exscript knows when the remote host is ready. For example,
consider the following script:

::

    1. show ip int brief
    2. write memory
    3. {enter}
    4. show configuration

Say that after executing line 2 of this script, the remote host asks for
a confirmation, saying something like this:

::

    Are you sure you want to overwrite the configuration? [confirm]

Because this answer does not contain a standard prompt, Exscript can
not recognize it. We have a deadlock. To fix this, we must tell
Exscript that a non-standard prompt should be expected. The
following change fixes the script:

::

    1. show ip int brief
    2. {connection.set_prompt(/\[confirm\]/)}
    3. write memory
    4. {connection.set_prompt()}
    5. {enter}
    6. show configuration

The second line tells Exscript to wait for "[confirm]" after
executing the following commands. Because of that, when the write memory
command was executed in line 3, the script does not deadlock (because
the remote host’s response includes "[confirm]"). In line 4, the prompt
is reset to it’s original value. This must be done, because otherwise
the script would wait for another "[confirm]" after executing line 5 and
line 6.

A Command Is Sent Too Soon
--------------------------

This happens when a prompt was incorrectly detected in the response of a
remote host. For example, consider using the following script:

::

    show interface descriptions{extract /^(\S+\d)/ as interfaces}
    show diag summary

Using this script, the following conversation may take place:

::

    1. router> show interface descriptions
    2. Interface              Status         Protocol Description
    3. Lo0                    up             up       Description of my router>
    4. PO0/0                  admin down     down     
    5. Serial1/0              up             up       My WAN link
    6. router> 

Note that line 3 happens to contain the string "Router>", which looks
like a prompt when it really is just a description. So after receiving
the ">" character in line 3, Exscript believes that the router is asking
for the next command to be sent. So it immediately sends the next
command ("show diag summary") to the router, even that the next prompt
was not yet received.

Note that this type of error may not immediately show, because the
router may actually accept the command even though it was sent before a
prompt was sent. It will lead to an offset however, and may lead to
errors when trying to capture the response. It may also lead to the
script terminating too early.

To fix this, make sure that the conversation with the remote host does
not include any strings that are incorrectly recognized as prompts. You
can do this by using the "connection.set_prompt(...)" function as
explained in the sections above.

The Connection Is Closed Too Soon
---------------------------------

This is essentially the same problem as explained under "A Command Is
Sent Too Soon". Whenever a prompt is (correctly or incorrectly)
detected, the next command is send to the remote host. If all commands
were already executed and the next prompt is received (i.e. the end of
the script was reached), the connection is closed.

To fix this, make sure that the conversation with the remote host does
not include any strings that are incorrectly recognized as prompts. You
can do this by using the "connection.set_prompt(...)" function as
explained in the sections above.
