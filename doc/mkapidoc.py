#!/usr/bin/env python
# Generates the *public* API documentation.
# Remember to hide your private parts, people!
import os, re, sys

project  = 'Exscript'
base_dir = os.path.join('..', 'src')
doc_dir  = 'api'

# Create the documentation directory.
if not os.path.exists(doc_dir):
    os.makedirs(doc_dir)

# Generate the API documentation.
cmd = 'epydoc ' + ' '.join(['--name', project,
                            r'--exclude ^Exscript\.AbstractMethod$',
                            r'--exclude ^Exscript\.AccountManager$',
                            r'--exclude ^Exscript\.HostAction$',
                            r'--exclude ^Exscript\.Log$',
                            r'--exclude ^Exscript\.Logfile$',
                            r'--exclude ^Exscript\.QueueListener$',
                            r'--exclude ^Exscript\.external$',
                            r'--exclude ^Exscript\.interpreter$',
                            r'--exclude ^Exscript\.parselib$',
                            r'--exclude ^Exscript\.protocols\.AbstractMethod$',
                            r'--exclude ^Exscript\.protocols\.StreamAnalyzer$',
                            r'--exclude ^Exscript\.protocols\.OsGuesser$',
                            r'--exclude ^Exscript\.protocols\.telnetlib$',
                            r'--exclude ^Exscript\.stdlib$',
                            r'--exclude ^Exscript\.workqueue$',
                            r'--exclude ^Exscript\.version$',
                            r'--exclude-introspect ^Exscript\.util\.sigintcatcher$',
                            r'--exclude ^TkExscript\.compat$',
                            '--html',
                            '--no-private',
                            '--introspect-only',
                            '--no-source',
                            '--no-frames',
                            '--inheritance=included',
                            '-v',
                            '-o %s' % doc_dir,
                            os.path.join(base_dir, project),
                            os.path.join(base_dir, 'TkExscript')])
print cmd
os.system(cmd)
