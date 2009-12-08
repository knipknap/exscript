import sys, os
from setuptools import setup, find_packages

# Import the file that contains the version number.
exscript_dir = os.path.join(os.path.dirname(__file__), 'src', 'Exscript')
sys.path.insert(0, exscript_dir)
from version import __version__

# Import the project description from the README.
readme = open('README').read()
start  = readme.index('\n\n')
end    = readme.index('\n\n=')
descr  = readme[start:end].strip()

# Run the setup.
setup(name             = 'Exscript',
      version          = __version__,
      description      = 'Script and template language for Telnet and SSH',
      long_description = descr,
      author           = 'Samuel Abels',
      author_email     = 'knipknap@gmail.com',
      license          = 'GPLv2',
      package_dir      = {'': 'src'},
      packages         = [p for p in find_packages('src')],
      scripts          = ['exscript'],
      install_requires = [],
      keywords         = ' '.join(['exscript',
                                   'telnet',
                                   'ssh',
                                   'network',
                                   'networking',
                                   'automate',
                                   'automation',
                                   'library']),
      url              = 'http://code.google.com/p/exscript/',
      classifiers      = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ])
