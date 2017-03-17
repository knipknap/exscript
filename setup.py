import sys
import os
from setuptools import setup, find_packages
from Exscript.version import __version__

# Import the project description from the README.
descr = '''
Exscript is a Python module and a template processor for automating network
connections over protocols such as Telnet or SSH. We attempt to create the
best possible set of tools for working with Telnet and SSH.
'''.strip()

# Run the setup.
setup(name             = 'Exscript',
      version          = __version__,
      description      = 'Automating Telnet and SSH',
      long_description = descr,
      author           = 'Samuel Abels',
      author_email     = 'knipknap@gmail.com',
      license          = 'MIT',
      package_dir      = {'Exscript': 'Exscript'},
      package_data     = {},
      packages         = find_packages(),
      scripts          = ['scripts/exscript'],
      install_requires = ['paramiko', 'pycrypto'],
      extras_require   = {},
      keywords         = ' '.join(['exscript',
                                   'telnet',
                                   'ssh',
                                   'network',
                                   'networking',
                                   'automate',
                                   'automation',
                                   'library']),
      url              = 'https://github.com/knipknap/exscript/',
      classifiers      = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ])
