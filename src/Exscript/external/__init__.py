import os, sys, warnings
sys.path.insert(0, os.path.dirname(__file__))
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category = DeprecationWarning)
    import paramiko
import SpiffSignal
sys.path.pop(0)
