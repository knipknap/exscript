#!/usr/bin/env python
## Author:      Samuel Abels
## Date:        2007-06-04
## Description: Use the Exscript interpreter with a multi threaded configuration
##              engine to execute commands on a list of hosts.
import sys, time, os, re, signal
sys.path.insert(0, 'lib')
import Exscript
from FooLib             import Interact
from FooLib             import OptionParser
from FooLib             import UrlParser
from WorkQueue          import WorkQueue
from WorkQueue          import Sequence
from TerminalConnection import *
from TerminalActions    import *

True  = 1
False = 0

__version__ = '0.9.8'

def usage():
    print "Exscript %s" % __version__
    print "Copyright (C) 2007 by Samuel Abels <http://debain.org>."
    print "Syntax: ./exscript.py [options] exscript [hostname [hostname ...]]"
    print "  -A, --authorize"
    print "                 When given, authorization is performed on devices that"
    print "                 support AAA (by default, $0 only authenticates)"
    print "  -c, --connections=NUM"
    print "                 Maximum number of concurrent connections."
    print "                 NUM is a number between 1 and 20, default is 5"
    print "      --csv-hosts FILE"
    print "                 Loads a list of hostnames and definitions from the given file."
    print "                 The first line of the file must have the column headers in the"
    print "                 following syntax:"
    print "                    hostname [variable] [variable] ..."
    print "                 where the fields are separated by tabs, \"hostname\" is the"
    print "                 keyword \"hostname\" and \"variable\" is a unique name under"
    print "                 which the column is accessed in the script."
    print "                 The following lines contain the hostname in the first column,"
    print "                 and the values of the variables in the following columns."
    print "  -d, --define PAIR"
    print "                 Defines a variable that is passed to the script."
    print "                 PAIR has the following syntax: <STRING>=<STRING>."
    print "      --hosts FILE"
    print "                 Loads a list of hostnames from the given file (one host per"
    print "                 line)."
    print "  -l, --logdir DIR"
    print "                 Logs any communication into the directory with the given name."
    print "                 Each filename consists of the hostname with \"_log\" appended."
    print "                 Errors are written to a separate file, where the filename"
    print "                 consists of the hostname with \".log.error\" appended."
    print "  -p, --protocol STRING"
    print "                 Specify which protocol to use to connect to the remote host."
    print "                 STRING is one of: telnet ssh"
    print "                 The default protocol is telnet."
    print "  -v, --verbose NUM"
    print "                 Print out debug information about the network activity."
    print "                 NUM is a number between 0 (min) and 5 (max)"
    print "  -V, --parser-verbose NUM"
    print "                 Print out debug information about the Exscript parser."
    print "                 NUM is a number between 0 (min) and 5 (max)"
    print "  -h, --help     Prints this help."

# Define default options.
default_options = [
  ('authorize',       'A',  False),
  ('no-echo',         None, False),
  ('connections=',    'c:', 1),
  ('csv-hosts=',      None, None),
  ('define=',         'd:', {'hostname': 'unknown'}),
  ('hosts=',          None, None),
  ('logdir=',         'l:', None),
  ('protocol=',       'p:', 'telnet'),
  ('verbose=',        'v:', 0),
  ('parser-verbose=', 'V:', 0),
  ('help',            'h',  False)
]

# Parse options.
try:
    options, args = OptionParser.parse_options(sys.argv, default_options)
    exscript      = args.pop(0)
    hostnames     = args
except:
    usage()
    sys.exit(1)
defines = dict([(hostname, options['define']) for hostname in hostnames])

# Show the help, if requested.
if options['help']:
    usage()
    sys.exit()

# If a filename containing hostnames AND VARIABLES was given, read it.
if options.get('csv-hosts') is not None:
    # Make sure that the file exists.
    if not os.path.exists(options.get('csv-hosts')):
        print "Error: File '%s' not found." % options.get('csv-hosts')
        sys.exit(1)

    # Open the file.
    try:
        file = open(options.get('csv-hosts'), 'r')
    except:
        print "Unable to open file '%s'. Perhaps you do not have read permission?"
        sys.exit(1)

    # Read the header.
    header = file.readline().rstrip()
    if re.search(r'^hostname\b', header) is None:
        print "Syntax error in CSV file header: File does not start with \"hostname\"."
        sys.exit(1)
    if re.search(r'^hostname(?:\t[^\t]+)*$', header) is None:
        print "Syntax error in CSV file header: %s" % header
        print "Make sure to separate columns by tabs."
        sys.exit(1)
    varnames = header.split('\t')
    varnames.pop(0)
    
    # Walk through all lines and create a map that maps hostname to definitions.
    last_hostname = ''
    for line in file:
        line     = line.rstrip('\r\n')
        values   = line.split('\t')
        hostname = values.pop(0).strip()

        # Add the hostname to our list.
        if hostname != last_hostname:
            print "Reading hostname", hostname, "from csv."
            hostnames.append(hostname)
            defines[hostname] = options['define'].copy()
            last_hostname = hostname

        # Define variables according to the definition.
        for i in range(0, len(varnames)):
            varname = varnames[i]
            try:
                value = values[i]
            except:
                value = ''
            if defines[hostname].has_key(varname):
                defines[hostname][varname].append(value)
            else:
                defines[hostname][varname] = [value]

# If a filename containing hostnames was given, read it.
if options.get('hosts') is not None:
    # Make sure that the file exists.
    if not os.path.exists(options.get('hosts')):
        print "Error: File '%s' not found." % options.get('hosts')
        sys.exit(1)

    # Open the file.
    try:
        file = open(options.get('hosts'), 'r')
    except:
        print "Unable to open file '%s'. Perhaps you do not have read permission?"
        sys.exit(1)

    # Read the hostnames.
    for line in file:
        hostname = line.strip()
        if hostname == '':
            continue
        hostnames.append(hostname)
        defines[hostname] = options['define'].copy()

# Create the log directory.
if options.get('logdir') is not None:
    if not os.path.exists(options.get('logdir')):
        print 'Creating log directory...'
        try:
            os.mkdir(options.get('logdir'))
        except:
            print 'Error: Unable to create directory %s.' % options.get('logdir')
            sys.exit(1)

# Make sure that all mandatory options are present.
if len(hostnames) <= 0:
    usage()
    sys.exit(1)

# Parse the exscript.
parser = Exscript.Parser(debug = options['parser-verbose'])
parser.define(**defines[hostnames[0]])
_, _, _, _, this_query = UrlParser.parse_url(hostnames[0])
parser.define(**this_query)
try:
    excode = parser.parse_file(exscript)
except Exception, e:
    if options['verbose'] > 0:
        raise
    print e
    sys.exit(1)

# Read username and password.
try:
    user, password = Interact.get_login()
except:
    sys.exit(1)

# Make sure that we shut down properly even when SIGINT or SIGTERM is sent.
def on_posix_signal(signum, frame):
    print '******************* SIGINT RECEIVED - SHUTTING DOWN! *******************'
    raise KeyboardInterrupt

signal.signal(signal.SIGINT,  on_posix_signal)
signal.signal(signal.SIGTERM, on_posix_signal)

try:
    # Initialize the workqueue.
    workqueue = WorkQueue(max_threads = options['connections'],
                          debug       = options['verbose'])

    print 'Starting engine...'
    workqueue.start()
    print 'Engine running.'

    # Build the action sequence.
    print 'Building sequence...'
    for hostname in hostnames:
        if options['verbose'] > 0:
            print 'Building sequence for %s.' % hostname

        # Prepare variables that are passed to the exscript interpreter.
        (this_proto,
         this_user,
         this_pass,
         this_host,
         this_query) = UrlParser.parse_url(hostname, options['protocol'])
        variables             = defines[hostname]
        variables['hostname'] = this_host
        variables.update(this_query)
        if this_user is None:
            this_user = user
            this_pass = password

        #FIXME: In Python > 2.2 we can (hopefully) deep copy the object instead of
        # recompiling numerous times.
        parser = Exscript.Parser(debug = options['parser-verbose'])
        parser.define(**variables)
        excode = parser.parse_file(exscript)
        excode.init(**variables)

        # One logfile per host.
        logfile       = None
        error_logfile = None
        if options.get('logdir') is None:
            sequence = Sequence(name = this_host)
        else:
            logfile       = os.path.join(options.get('logdir'), this_host + '.log')
            error_logfile = logfile + '.error'
            sequence      = LoggedSequence(name          = this_host,
                                           logfile       = logfile,
                                           error_logfile = error_logfile)

        # Choose the protocol.
        if this_proto == 'telnet':
            protocol = Telnet
        elif this_proto == 'ssh':
            protocol = SSH
        else:
            print 'Unsupported protocol %s' % this_proto
            continue

        # Build the sequence.
        echo = options['connections'] == 1 and options['no-echo'] == 0
        sequence.add(Connect(protocol, this_host, echo = echo))
        sequence.add(Authenticate(this_user, this_pass))
        if options['authorize']:
            sequence.add(Authorize(password))
        sequence.add(CommandScript(excode))
        sequence.add(Command('exit'))
        sequence.add(Close())
        workqueue.enqueue(sequence)

    # Wait until the engine is finished.
    print 'All actions enqueued.'
    while workqueue.get_queue_length() > 0:
        #print '%s jobs left, waiting.' % workqueue.get_queue_length()
        time.sleep(1)
    print 'Shutting down engine...'
except KeyboardInterrupt:
    print 'Interrupt caught succcessfully.'
    print '%s unfinished jobs.' % workqueue.get_queue_length()
    sys.exit(1)

workqueue.shutdown()

print 'Engine shut down.'
