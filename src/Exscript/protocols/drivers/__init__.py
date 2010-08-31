from aix       import AIXDriver
from enterasys import EnterasysDriver
from generic   import GenericDriver
from ios       import IOSDriver
from ios_xr    import IOSXRDriver
from junos     import JunOSDriver
from one_os    import OneOSDriver
from shell     import ShellDriver
from vrp       import VRPDriver

driver_list = (AIXDriver,
               EnterasysDriver,
               GenericDriver,
               IOSDriver,
               IOSXRDriver,
               JunOSDriver,
               OneOSDriver,
               ShellDriver,
               VRPDriver)
