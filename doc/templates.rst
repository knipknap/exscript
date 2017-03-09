Exscript Templates
==================

Simple example
--------------

The simplest possible template is one that contains only the commands
that are sent to the remote host. For example, the following Exscript
template can be used to retrieve the response of the ls -l and df
commands from a unix host::

    ls -l
    df

Comments
--------

Lines starting with a hash ("#") are interpreted as comments and
ignored. For example::

    1. # This line is ignored...
    2. {if __hostname__ is "test"}
    3.   # ...and so is this one.
    4. {end}

Using Variables
---------------

The following template uses a variable to execute the ls command with a
filename as an argument::

    ls -l $filename

When executing it from the command line, use::

    exscript -d filename=.profile my.exscript localhost 

Note that the -d switch allows passing variables into the template.
The example executes the command ls -l .profile. You can also assign a
value to a variable within a template::

    {filename = ".profile"}
    ls -l $filename

You may also use variables in strings by prefixing them with the "$"
character::

    1. {test = "my test"}
    2. {if "my test one" is "$test one"}
    3.   # This matches!
    4. {end}

In the above template line 3 is reached. If you don’t want the "$"
character to be interpreted as a variable, you may prefix it with a
backslash::

    1. {test = "my test"}
    2. {if "my test one" is "\$test one"}
    3.   # This does not match
    4. {end}

Adding Variables To A List
--------------------------

In Exscript, every variable is a list. You can also merge two lists
by using the "append" keyword::

    1. {
    2.   test1 = "one"
    3.   test2 = "two"
    4.   append test2 to test1
    5. }

This results in the "test1" variable containing two items, "one" and
"two".

Using Built-in Variables
------------------------

The following variables are available in any Exscript template, even
if they were not explicitly passed in:

#. ``__hostname__`` contains the hostname that was used to open the
   current connection.

#. ``__response__`` contains the response of the remote host that
   was received after the execution of the last command.

Built-in variables are used just like any other variable. You can also
assign a new value to a built-in variable in the same way.

Using Expressions
-----------------

An expression is a combination of values, variables, operators, and
functions that are interpreted (evaluated) according to particular rules
and that produce a return value. For example, the following code is an
expression::

    name is "samuel" and 4 * 3 is not 11

In this expression, *name* is a variable, *is*, *is not*, and * are
operators, and *"samuel"*, *4*, *3*, and *11* are values. The return
value of this particular expression is *true*.

In Exscript, expressions are used in many places, such as
if-conditions or variable assignments. The following operators may be
used in an expression.

Priority 1 Operators
~~~~~~~~~~~~~~~~~~~~

#. ``*`` multiplies the operators (numerically).

#. ``/`` divides the operators (numerically).

Priority 2 Operators
~~~~~~~~~~~~~~~~~~~~

#. ``+`` adds the operators (numerically).

#. ``-`` subtracts the operators (numerically).

Priority 3 Operators
~~~~~~~~~~~~~~~~~~~~

#. ``.`` concatenates two strings.

Priority 4 Operators
~~~~~~~~~~~~~~~~~~~~

#. ``is`` tests for equality. If both operators are lists, only the first
   item in the list is compared.

#. ``is not`` produces the opposite result from is.

#. ``in`` tests whether the left string equals any of the items in the
   list given as the right operator.

#. ``not in`` produces the opposite result from in.

#. ``matches`` tests whether the left operator matches the regular
   expression that is given as the right operator.

#. ``ge`` tests whether the left operator is (numerically) greater than or
   equal to the right operator.

#. ``gt`` tests whether the left operator is (numerically) greater than
   the right operator.

#. ``le`` tests whether the left operator is (numerically) less than or
   equal to the right operator.

#. ``lt`` tests whether the left operator is (numerically) less than the
   right operator.

Priority 5 Operators
~~~~~~~~~~~~~~~~~~~~

#. ``not`` inverts the result of a comparison.

Priority 6 Operators
~~~~~~~~~~~~~~~~~~~~

#. ``and`` combines two tests such that a logical AND comparison is made.
   If the left operator returns FALSE, the right operator is not
   evaluated.

#. ``or`` combines two tests such that a logical OR comparison is made. If
   the left operator returns TRUE, the right operator is not evaluated.

Using Hexadecimal Or Octal Numbers
----------------------------------

Exscript also supports hexadecimal and octal numbers using the
following syntax::

    {
      if 0x0a is 012
        sys.message("Yes")
      else
        sys.message("No")
      end
    }

Using Regular Expressions
-------------------------

At some places Exscript uses Regular Expressions. These are NOT the
same as the expressions documented above, and if you do not know what
regular expressions are it is recommended that you read a tutorial on
regular expressions first.

Exscript regular expressions are similar to Perl and you may also
append regular expression modifiers to them. For example, the following
is a valid regular expression in Exscript::

    /^cisco \d+\s+\w/i

Where the appended "i" is a modifier (meaning case-insensitive). A full
explanation of regular expressions is not given here, because plenty of
introductions have been written already and may be found with the
internet search engine of your choice.

Built-in Commands
-----------------

By default, any content of an Exscript template is sent to the remote host.
However, you can also add instructions with special meanings. Such
instructions are enclosed by curly brackets (``{`` and ``{``).
The following commands all use this syntax.

Extracting Data From A Response
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Exscript lets you parse the response of a remote host using regular
expressions. If you do not know what regular expressions are, please
read a tutorial on regular expressions first.

extract ... into ...
~~~~~~~~~~~~~~~~~~~~

If you already know what regular expressions are, consider the following
template::

    ls -l {extract /^(d.*)/ into directories}

The extract command matches each line of the response of "ls -l" against
the regular expression ``/(d.*)/`` and then appends the result of the
first match group (a match group is a part of a regular
expression that is enclosed by brackets) to the list variable
named directories.

You can also extract the value of multiple match groups using the
following syntax::

    ls -l {extract /^(d\S+)\s.*\s(\S+)$/ into modes, directories}

This extracts the mode and the directory name from each line and appends
them to the modes and directories lists respectively. You can also apply
multiple matches to the same response using the following syntax::

    ls -l {
      extract /^[^d].*\s(\S+)$/ into files
      extract /^d.*\s(\S+)$/    into directories
    }

There is no limit to the number of extract statements.

extract ... into ... from ...
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When used without the "from" keyword, "extract" gets the values from the
last command that was executed. You may however also instruct Exscript
to extract the values from a variable. The following example shows how
this may be done.

::

    ls -l {
      extract /^(.*)/  into lines
      extract /^(d.*)/ into directories from lines
    }

extract ... as ...
~~~~~~~~~~~~~~~~~~

The "as" keyword is similar to "into", the difference being that with
as, the destination variable is cleared before new values are appended.

::

    ls -l {extract /^(d.*)/ as directories}

"as" may be used anywhere where "into" is used.

If-Conditions
^^^^^^^^^^^^^

You can execute commands depending on the runtime value of a variable or
expression.

if ... end
~~~~~~~~~~

The following Exscript template executes the ``ls`` command only if
``ls -l .profile`` did not produce a result::

    ls -l .profile {extract /(\.profile)$/ as found}
    {if found is not ".profile"}
      ls
    {end}

if ... else ... end
~~~~~~~~~~~~~~~~~~~

You can also add an else condition::

    ls -l .profile {extract /(\.profile)$/ as found}
    {if found is not ".profile"}
      ls
    {else}
      touch .profile
    {end}

if ... else if ...
~~~~~~~~~~~~~~~~~~

You can perform multiple matches using else if::

    ls -l .profile {extract /(.*profile)$/ as found}
    {if found is ".profile"}
      ls
    {else if found matches /my_profile/}
      ls -l p*
    {else}
      touch .profile
    {end}

Loops
^^^^^

You can execute commands multiple times using the "loop" statement. The
following Exscript template executes the "ls" command three times::

    {number = 0}
    {loop until number is 3}
      {number = number + 1}
      ls $directory
    {end}

Similarly, the while statement may be used. The following script is
equivalent::

    {number = 0}
    {loop while number is not 3}
      {number = number + 1}
      ls $directory
    {end}

Another alternative is using the "loop from ... to ..." syntax, which
allows you to specify a range of integers::

    # Implicit "counter" variable.
    {loop from 1 to 3}
      ls $directory$counter
    {end}

    # Explicit variable name.
    {loop from 1 to 3 as number}
      ls $directory$number
    {end}

Loops And Lists
^^^^^^^^^^^^^^^

The following Exscript template uses the ls command to show the content of a
list of subdirectories::

    ls -l {extract /^d.*\s(\S+)$/ as directories}
    {loop directories as directory}
      ls $directory
    {end}

You can also walk through multiple lists at once, as long as they have
the same number of items in it::

    ls -l {extract /^(d\S+)\s.*\s(\S+)$/ as modes, directories}
    {loop modes, directories as mode, directory}
      echo Directory has the mode $mode
      ls $directory
    {end}

List loops can also be combined with the until or while statement seen
in the previous section::

    ls -l {extract /^d.*\s(\S+)$/ as directories}
    {loop directories as directory until directory is "my_subdir"}
      ls $directory
    {end}

Functions
^^^^^^^^^

Exscript provides builtin functions with the following syntax::

    type.function(EXPRESSION, [EXPRESSION, ...])

For example, the following function instructs Exscript to wait for
10 seconds::

    {sys.wait(10)}

For a list of supported functions please check here:

.. automodule:: Exscript.stdlib

Exiting A Script
^^^^^^^^^^^^^^^^

fail "message"
~~~~~~~~~~~~~~

The "fail" keyword may be used where a script should terminate
immediately.

::

    show something
    {fail "Error: Failed!"}
    show something else

In this script, the "show something else" line is never reached.

fail "message" if ...
~~~~~~~~~~~~~~~~~~~~~

It is also possible to fail only if a specific condition is met. The
following snippet terminates only if a Cisco router does not have a POS
interface::

    show ip int brie {
      extract /^(POS)\S+/ as pos_interfaces
      fail "No POS interface found!" if "POS" not in pos_interfaces
    }

Error Handling
^^^^^^^^^^^^^^

Exscript attempts to detect errors, such as commands that are not
understood by the remote host. By default, Exscript considers any
response that includes one of the following strings to be an error::

    invalid
    incomplete
    unrecognized
    unknown command
    [^\r\n]+ not found

If this default configuration does not suit your needs, you can override
the default, setting it to any regular expression of your choice using
the following function::

    {connection.set_error(/[Ff]ailed/)}

Whenever such an error is detected, the currently running Exscript template
is cancelled on the current host. For example, when the following
script is executed on a Cisco router, it will fail because there is no
ls command::

    ls -l
    show ip int brief

The "show ip int brief" command is not executed, because an error is
detected at "ls -l" at runtime.

If you want to execute the command regardless, you can wrap the "ls"
command in a "try" block::

    {try}ls -l{end}
    show ip int brief

You can add as many commands as you like in between a try block. For
example, the following will also work::

    {try}
      ls -l
      df
      show running-config
    {end}
    show ip int brief
