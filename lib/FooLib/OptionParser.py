import re
from getopt import getopt

True  = 1
False = 0

def parse_options(argv, options):
    """
    Parses the options into the given list, returns a tuple containing the new
    list and the remaining arguments.
    """
    # Use getopt to parse the options.
    short = ''.join([option[1] or '' for option in options])
    long  = [option[0] for option in options]
    try:
        opts, args = getopt(argv[1:], short, long)
    except:
        raise Exception("Invalid arguments")
    
    # Copy the default options into a hash.
    option_hash = {}
    for option in options:
         long              = option[0].replace('=', '')
         option_hash[long] = option[2]

    # Walk through all options and sort them into a hash.
    for key, value in opts:
        found = False
        for option in options:
            long  = option[0] or ''
            short = option[1] or ''
            if long.endswith('='):
                long  = long.replace('=', '')
                short = short.replace(':', '')
            if key not in ('--'+long, '-'+short):
                continue
            found = True
            #print "Short:", short, "Long:", long

            # Flags.
            if not option[0].endswith('='):
                option_hash[long] = True
                continue

            # Key/value pairs.
            if type(option_hash[long]) == type({}):
                value = value.split('=')
                option_hash[long][value[0]] = value[1]

            # Strings.
            elif re.match('^\d+$', value) is None:
                option_hash[long] = value

            # Integer.
            else:
                option_hash[long] = int(value)
        if not found:
            raise Exception("Invalid argument '%s'" % key)

    return (option_hash, args)
