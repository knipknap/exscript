"""
Runs the command line tool ``exscript``: ``python -m Exscript``.
"""

import sys

from .cli import main

if __name__ == '__main__':
    sys.exit(main())
