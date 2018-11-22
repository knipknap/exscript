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
from Exscript.protocols.drivers.driver import Driver
from Exscript.protocols.drivers.adtran import AdtranDriver
from Exscript.protocols.drivers.aironet import AironetDriver
from Exscript.protocols.drivers.aix import AIXDriver
from Exscript.protocols.drivers.arbor_peakflow import ArborPeakflowDriver
from Exscript.protocols.drivers.brocade import BrocadeDriver
from Exscript.protocols.drivers.enterasys import EnterasysDriver
from Exscript.protocols.drivers.generic import GenericDriver
from Exscript.protocols.drivers.hp_pro_curve import HPProCurveDriver
from Exscript.protocols.drivers.ios import IOSDriver
from Exscript.protocols.drivers.nxos import NXOSDriver
from Exscript.protocols.drivers.ios_xr import IOSXRDriver
from Exscript.protocols.drivers.ace import ACEDriver
from Exscript.protocols.drivers.junos import JunOSDriver
from Exscript.protocols.drivers.junos_erx import JunOSERXDriver
from Exscript.protocols.drivers.mrv import MRVDriver
from Exscript.protocols.drivers.one_os import OneOSDriver
from Exscript.protocols.drivers.shell import ShellDriver
from Exscript.protocols.drivers.smart_edge_os import SmartEdgeOSDriver
from Exscript.protocols.drivers.vrp import VRPDriver
from Exscript.protocols.drivers.sros import SROSDriver
from Exscript.protocols.drivers.aruba import ArubaDriver
from Exscript.protocols.drivers.enterasys_wc import EnterasysWCDriver
from Exscript.protocols.drivers.fortios import FortiOSDriver
from Exscript.protocols.drivers.bigip import BigIPDriver
from Exscript.protocols.drivers.isam import IsamDriver
from Exscript.protocols.drivers.zte import ZteDriver
from Exscript.protocols.drivers.vxworks import VxworksDriver
from Exscript.protocols.drivers.ericsson_ban import EricssonBanDriver
from Exscript.protocols.drivers.rios import RIOSDriver
from Exscript.protocols.drivers.eos import EOSDriver
from Exscript.protocols.drivers.cienasaos import CienaSAOSDriver
from Exscript.protocols.drivers.icotera import IcoteraDriver
from Exscript.protocols.drivers.zyxel import ZyxelDriver

driver_classes = []
drivers = []
driver_map = {}


def isdriver(o):
    return inspect.isclass(o) and issubclass(o, Driver) and not o is Driver

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
