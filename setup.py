import sys

from setuptools import find_packages, setup

sys.path.insert(0, 'Exscript')
from version import __version__

# Import the project description from the README.
descr = '''
Exscript is a Python module and a template processor for automating network
connections over protocols such as Telnet or SSH/Netconf. We attempt to create
the best possible set of tools for working with Telnet and SSH/Netconf.
'''.strip()

# Run the setup.
setup(name             = 'Exscript',
      version          = __version__,
      description      = 'Automating Telnet and SSH/Netconf',
      long_description = descr,
      author           = 'Samuel Abels',
      author_email     = 'knipknap@gmail.com',
      license          = 'MIT',
      package_dir      = {'Exscript': 'Exscript'},
      package_data     = {},
      packages         = find_packages(),
      scripts          = ['scripts/exscript', 'scripts/otp'],
      install_requires = [
          'configparser',
          'lxml',
          'ncclient>=0.7,<1',
          'paramiko>=2.2,<5',
          'pycryptodomex',
      ],
      extras_require   = {
          'otel': [
              'opentelemetry-api>=1.12',
              'opentelemetry-sdk>=1.12',
              'opentelemetry-instrumentation>=0.42b0',
          ],
      },
      keywords         = ' '.join(['exscript',
                                   'telnet',
                                   'ssh',
                                   'netconf',
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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ])
