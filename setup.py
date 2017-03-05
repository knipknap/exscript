import sys
import os
from setuptools import setup, find_packages
from Exscript.version import __version__

# Import the project description from the README.
readme = open('README.md').read()
start  = readme.index('\n\n')
end    = readme.index('\n\nLinks')
descr  = readme[start:end].strip()

# Run the setup.
setup(name             = 'Exscript',
      version          = __version__,
      description      = 'Template language for automating Telnet and SSH',
      long_description = descr,
      author           = 'Samuel Abels',
      author_email     = 'knipknap@gmail.com',
      license          = 'GPLv2',
      package_dir      = {'Exscript': 'Exscript'},
      package_data     = {},
      packages         = find_packages(),
      scripts          = ['exscript'],
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
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ])
