# Copyright (C) 2007 Samuel Abels, http://debain.org
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import sys, copy, threading
from Host           import Host
from FunctionRunner import FunctionRunner
from Interpreter    import Parser

True  = 1
False = 0

class TemplateRunner(FunctionRunner):
    """
    Opens and parses an exscript template and executes it on one or 
    more hosts.
    """

    def __init__(self, **kwargs):
        """
        Constructor.

        @type  kwargs: dict
        @param kwargs: In addition to the options supported by FunctionRunner,
                       the following options are provided:
            - no_prompt: Whether the compiled program should wait for a 
            prompt each time after the Exscript sent a command to the 
            remote host.
            - strip_command: Whether the first line of each response (which
            typically contains the command) is stripped.
            - template_file: The template file to be executed.
            - template: The template to be executed.
            - parser_verbose: The verbosity level of the parser.
        """
        self.compiled    = None
        self.global_vars = {}
        self.code        = None
        self.file        = None
        self.parser      = None
        self.parser_lock = threading.Lock()
        FunctionRunner.__init__(self, self._run_template, **kwargs)


    def set_options(self, **kwargs):
        """
        Set the given options of the template runner.
        """
        FunctionRunner.set_options(self, **kwargs)
        self.no_prompt      = kwargs.get('no_prompt',      0)
        self.strip_command  = kwargs.get('strip_command',  1)
        self.parser_verbose = kwargs.get('parser_verbose', 0)
        self.parser_lock.acquire()
        self.parser = self._get_parser()
        self.parser_lock.release()
        if self.options.has_key('template'):
            self.read_template(self.options.get('template'))
        if self.options.has_key('template_file'):
            self.read_template_from_file(self.options.get('template_file'))


    def _get_parser(self):
        return Parser(debug         = self.parser_verbose,
                      no_prompt     = self.no_prompt,
                      strip_command = self.strip_command)


    def define(self, **kwargs):
        """
        Defines the given variables such that they may be accessed from 
        within the Exscript template.

        @type  kwargs: dict
        @param kwargs: Variables to make available to the Exscript.
        """
        self.global_vars.update(kwargs)


    def read_template(self, template):
        """
        Reads the given Exscript template, using the given options.
        MUST be called before run() is called, either directly or through 
        read_template_from_file().

        @type  template: string
        @param template: An Exscript template.
        """
        # Assign a "fake" host to the parser, as the included variables allow
        # for checking the script for undefined variables.
        if len(self.hosts) == 0:
            host = Host('unknown')
            host.set('hostname', 'unknown')
        else:
            host = self.hosts[0]

        # Assign to the parser.
        self.parser_lock.acquire()
        self.parser.define(**self.global_vars)
        self.parser.define(**host.vars)
        self.parser.define(__filename__ = self.file)
        self.parser.define(hostname     = host.get_name())

        # Parse the Exscript.
        try:
            self.compiled = self.parser.parse(template)
            self.code     = template
        except Exception, e:
            self.parser_lock.release()
            if self.verbose > 0:
                raise
            print e
            sys.exit(1)
        self.parser_lock.release()


    def read_template_from_file(self, filename):
        """
        Loads the Exscript file with the given name, and calls 
        read_template() to process the code using the given options.

        @type  filename: string
        @param filename: A full filename.
        """
        file_handle = open(filename, 'r')
        self.file   = filename
        template    = file_handle.read()
        file_handle.close()
        self.read_template(template)


    def _run_template(self, exscript, host, conn):
        """
        Compiles the current Exscript template and executes it.
        """
        if self.compiled is None:
            msg = 'An Exscript was not yet read using read_template().'
            raise Exception(msg)

        # Pass variables to the Exscript interpreter.
        variables = dict()
        variables.update(self.global_vars)
        variables['hostname'] = host.get_address()
        variables.update(host.vars)
        self.parser_lock.acquire()
        self.parser.define(**variables)

        # Parse the Exscript template.
        #FIXME: In Python > 2.2 we can (hopefully) deep copy the object instead of
        # recompiling numerous times.
        if self.options.has_key('filename'):
            file = self.options.get('filename')
            try:
                compiled = self.parser.parse_file(file)
            except:
                self.parser_lock.release()
                raise
        else:
            code = self.options.get('code', self.code)
            try:
                compiled = self.parser.parse(code)
            except:
                self.parser_lock.release()
                raise
        self.parser_lock.release()

        #compiled = copy.deepcopy(self.compiled)
        compiled.init(**variables)
        compiled.define(__filename__   = self.file)
        compiled.define(__runner__     = self)
        compiled.define(__exscript__   = exscript)
        compiled.define(__connection__ = conn)
        compiled.define(__user__       = host.get_username())
        compiled.define(__password__   = host.get_password())
        compiled.execute()
        return True
