#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import inspect

from .ace import ACEDriver as ACEDriver
from .adtran import AdtranDriver as AdtranDriver
from .aironet import AironetDriver as AironetDriver
from .aix import AIXDriver as AIXDriver
from .arbor_peakflow import ArborPeakflowDriver as ArborPeakflowDriver
from .aruba import ArubaDriver as ArubaDriver
from .bigip import BigIPDriver as BigIPDriver
from .brocade import BrocadeDriver as BrocadeDriver
from .cienasaos import CienaSAOSDriver as CienaSAOSDriver
from .driver import Driver
from .enterasys import EnterasysDriver as EnterasysDriver
from .enterasys_wc import EnterasysWCDriver as EnterasysWCDriver
from .eos import EOSDriver as EOSDriver
from .ericsson_ban import EricssonBanDriver as EricssonBanDriver
from .fortios import FortiOSDriver as FortiOSDriver
from .generic import GenericDriver as GenericDriver
from .hp_pro_curve import HPProCurveDriver as HPProCurveDriver
from .icotera import IcoteraDriver as IcoteraDriver
from .ios import IOSDriver as IOSDriver
from .ios_xr import IOSXRDriver as IOSXRDriver
from .isam import IsamDriver as IsamDriver
from .junos import JunOSDriver as JunOSDriver
from .junos_erx import JunOSERXDriver as JunOSERXDriver
from .mrv import MRVDriver as MRVDriver
from .nxos import NXOSDriver as NXOSDriver
from .one_os import OneOSDriver as OneOSDriver
from .rios import RIOSDriver as RIOSDriver
from .shell import ShellDriver as ShellDriver
from .smart_edge_os import SmartEdgeOSDriver as SmartEdgeOSDriver
from .sp_vxoa import SilverPeakVXOADriver as SilverPeakVXOADriver
from .sros import SROSDriver as SROSDriver
from .vrp import VRPDriver as VRPDriver
from .vxworks import VxworksDriver as VxworksDriver
from .zte import ZteDriver as ZteDriver
from .zyxel import ZyxelDriver as ZyxelDriver

driver_classes: list[type[Driver]] = []
drivers: list[Driver] = []
driver_map: dict[str, Driver] = {}


def isdriver(o):
    return inspect.isclass(o) and issubclass(o, Driver) and o is not Driver

def add_driver(cls):
    driver = cls()
    driver_classes.append(cls)
    drivers.append(driver)
    driver_map[driver.name] = driver

def disable_driver(name):
    driver = driver_map.pop(name)
    drivers.pop(driver)
    driver_classes.pop(driver.__class__)

# Load built-in drivers.
for name, obj in list(locals().items()):
    if isdriver(obj):
        add_driver(obj)
driver_map['unknown'] = driver_map['generic']
