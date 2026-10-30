"""
The version of the installed Exscript distribution.
"""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version('Exscript')
except PackageNotFoundError:  # used from a source tree without installation
    __version__ = 'DEVELOPMENT'
