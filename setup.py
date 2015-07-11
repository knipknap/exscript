import sys
import os
from setuptools import setup, find_packages

# Import the file that contains the version number.
exscript_dir = os.path.join(os.path.dirname(__file__), 'src', 'Exscript')
sys.path.insert(0, exscript_dir)
from version import __version__

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
      package_dir      = {'': 'src',
                          'Exscript':   os.path.join('src', 'Exscript'),
                          'Exscriptd':  os.path.join('src', 'Exscriptd'),
                          'TkExscript': os.path.join('src', 'TkExscript')},
      package_data     = {'Exscriptd': [
                            os.path.join('config', 'exscriptd.in'),
                            os.path.join('config', 'main.xml.in'),
                         ]},
      packages         = find_packages('src'),
      scripts          = ['exscript',
                          'exscriptd',
                          'exscriptd-config',
                          'exclaim'],
      install_requires = ['paramiko', 'pycrypto'],
      extras_require   = {
                            'Exscriptd': ['sqlalchemy', 'lxml'],
                            'TkExscript': ['tkinter'],
                         },
      keywords         = ' '.join(['exscript',
                                   'exscripd',
                                   'exclaim',
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
