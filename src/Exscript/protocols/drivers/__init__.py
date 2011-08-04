import inspect
from Exscript.protocols.drivers.driver         import Driver
from Exscript.protocols.drivers.aix            import AIXDriver
from Exscript.protocols.drivers.arbor_peakflow import ArborPeakflowDriver
from Exscript.protocols.drivers.enterasys      import EnterasysDriver
from Exscript.protocols.drivers.generic        import GenericDriver
from Exscript.protocols.drivers.ios            import IOSDriver
from Exscript.protocols.drivers.ios_xr         import IOSXRDriver
from Exscript.protocols.drivers.junos          import JunOSDriver
from Exscript.protocols.drivers.junos_erx      import JunOSERXDriver
from Exscript.protocols.drivers.one_os         import OneOSDriver
from Exscript.protocols.drivers.shell          import ShellDriver
from Exscript.protocols.drivers.smart_edge_os  import SmartEdgeOSDriver
from Exscript.protocols.drivers.vrp            import VRPDriver
from Exscript.protocols.drivers.sros           import SROSDriver

def isdriver(o):
    return inspect.isclass(o) and issubclass(o, Driver) and not o is Driver

driver_classes = [obj for name, obj in locals().items() if isdriver(obj)]
drivers        = [d() for d in driver_classes]
driver_map     = dict((d.name, d) for d in drivers)
driver_map['unknown'] = driver_map['generic']
