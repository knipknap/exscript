import inspect
from driver    import Driver
from aix       import AIXDriver
from enterasys import EnterasysDriver
from generic   import GenericDriver
from ios       import IOSDriver
from ios_xr    import IOSXRDriver
from junos     import JunOSDriver
from one_os    import OneOSDriver
from shell     import ShellDriver
from vrp       import VRPDriver

def isdriver(o):
    return inspect.isclass(o) and issubclass(o, Driver) and not o is Driver

driver_classes = [obj for name, obj in locals().items() if isdriver(obj)]
drivers        = [d() for d in driver_classes]
driver_map     = dict((d.name, d) for d in drivers)
