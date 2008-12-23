from setuptools import setup, find_packages
setup(name             = 'Exscript',
      version          = '0.9.13',
      description      = 'Script and template language for Telnet and SSH',
      long_description = \
"""
Exscript is a script and template language for automating network connections 
over protocols such as Telnet or SSH. Exscript is targeted at non-developers 
and developers alike.

Exscript is often used to automate sessions with routers from Cisco, Juniper, 
Huawei, or others. Are you an administrator who often configures machines 
running Linux/Unix, IOS, IOS-XR, JunOS, VRP, or any other operating system 
that can be used with a terminal? Then Exscript is for you!

Exscript is in some ways comparable to Expect, but has some unique features 
that make it a lot easier to use and understand for non-developers. 
""",
      author           = 'Samuel Abels',
      author_email     = 'cheeseshop.python.org@debain.org',
      license          = 'GPLv2',
      package_dir      = {'': 'src'},
      packages         = [p for p in find_packages('src')],
      scripts          = ['exscript'],
      install_requires = ['termconnect'],
      keywords         = 'exscript telnet ssh automate automation library',
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
