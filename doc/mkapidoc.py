#!/usr/bin/env python
# Generates the *public* API documentation.
# Remember to hide your private parts, people!
import os, re, sys

project  = 'Exscript'
base_dir = os.path.join('..', 'src', project)
doc_dir  = 'api'

# Create the documentation directory.
if not os.path.exists(doc_dir):
    os.makedirs(doc_dir)

# Generate the API documentation.
os.system('epydoc ' + ' '.join(['--name', project,
                                '--exclude Exscript.version',
                                '--exclude Exscript.interpreter',
                                '--exclude Exscript.helpers',
                                '--exclude Exscript.FunctionAction',
                                '--exclude Exscript.AccountManager',
                                '--exclude Exscript.workqueue',
                                '--exclude Exscript.stdlib',
                                '--exclude Exscript.protocols.AbstractMethod',
                                '--exclude Exscript.protocols.telnetlib',
                                '--exclude Exscript.util.otp',
                                '--html',
                                '--no-private',
                                '--no-source',
                                '--no-frames',
                                '--inheritance=included',
                                '-v',
                                '-o %s' % doc_dir,
                                base_dir]))
