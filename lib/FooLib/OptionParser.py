# Copyright (C) 2007 Samuel Abels, http://debain.org
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
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
