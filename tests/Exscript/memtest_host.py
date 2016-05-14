from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
from builtins import range
# This script is not meant to provide a fully automated test, it's
# merely a hack/starting point for investigating memory consumption
# manually. The behavior also depends heavily on the version of meliae.
from meliae import scanner, loader
from Exscript import Account, Host

hostlist = [Host(str(i)) for i in range(1, 10000)]
#accountlist = [Account(str(i)) for i in range(1, 10000)]

scanner.dump_all_objects('test.dump')
om = loader.load('test.dump')
print(om.summarize())
