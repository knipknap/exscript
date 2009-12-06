# Copyright (C) 2007-2009 Samuel Abels.
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
import os, re
from Exscript.util.crypt import otp
from Exception           import TransportException, LoginFailure
from Transport           import Transport,         \
                                cisco_user_re,     \
                                junos_user_re,     \
                                unix_user_re,      \
                                iosxr_prompt_re,   \
                                pass_re,           \
                                skey_re,           \
                                huawei_re,         \
                                login_fail_re

True  = 1
False = 0

class Dummy(Transport):
    """
    A protocol adapter that emulates a remote device.
    """
    LOGIN_TYPE_PASSWORDONLY, \
    LOGIN_TYPE_USERONLY, \
    LOGIN_TYPE_BOTH, \
    LOGIN_TYPE_NONE = range(1, 5)

    PROMPT_STAGE_USERNAME, \
    PROMPT_STAGE_PASSWORD, \
    PROMPT_STAGE_CUSTOM = range(1, 4)

    def __init__(self, **kwargs):
        """
        @type  kwargs: dict
        @param kwargs: In addition to the kwargs of Transport,
        this adapter supports the following:
         - banner: A string to show as soon as the connection is opened.
         - login_type:
         - strict: Whether to raise when a given command has no handler.
        """
        Transport.__init__(self, **kwargs)
        self.connected_host = None
        self.connected_port = None
        self.banner         = kwargs.get('banner',     None)
        self.login_type     = kwargs.get('login_type', self.LOGIN_TYPE_BOTH)
        self.strict         = kwargs.get('strict',     False)
        self.prompt_stage   = self.PROMPT_STAGE_USERNAME
        self.custom_prompt  = None
        self.logged_in      = False
        self.buffer         = ''
        self.response       = None
        self.response_list  = []


    def is_dummy(self):
        return True


    def _get_custom_prompt(self):
        port   = str(self.connected_port)
        prompt = str(self.connected_host) + ':' + port + '> '
        return self.custom_prompt or prompt


    def _get_prompt(self):
        if self.prompt_stage == self.PROMPT_STAGE_USERNAME:
            if self.login_type == self.LOGIN_TYPE_USERONLY:
                self.prompt_stage = self.PROMPT_STAGE_CUSTOM
            else:
                self.prompt_stage = self.PROMPT_STAGE_PASSWORD
            return 'Username: '
        elif self.prompt_stage == self.PROMPT_STAGE_PASSWORD:
            self.prompt_stage = self.PROMPT_STAGE_CUSTOM
            return 'Password: '
        elif self.prompt_stage == self.PROMPT_STAGE_CUSTOM:
            self.logged_in = True
            return self._get_custom_prompt()
        else:
            assert False # No such stage.


    def _create_autoprompt_handler(self, handler):
        def append_prompt(data):
            if isinstance(handler, str):
                return handler + self._get_custom_prompt()
            return handler(data) + self._get_custom_prompt()
        return append_prompt


    def _expect_any(self, prompt_list):
        i = 0
        for prompt in prompt_list:
            matches = prompt.search(self.buffer)
            if matches is not None:
                prompt_len    = len(matches.group())
                self.response = self.buffer[:-prompt_len]
                self.buffer   = ''
                #print "MATCH", i, repr(prompt.pattern), repr(response)
                return (i, matches, self.response)
            i += 1
        return None


    def _say(self, string):
        self.buffer += self._receive_cb(string)


    def add_command_handler(self, command, response):
        """
        Register a regular expression such that whenever a string sent to the 
        remote host matches, the given response handler is called.

        If the given response handler is a string, that string is sent as the 
        response to any command that matches the given regular expression.

        @type  command: str|regex
        @param command: A string or a compiled regular expression.
        @type  response: function or string
        @param response: A reponse, or a response handler.
        """
        if isinstance(command, str):
            command = re.compile(command)
        elif not hasattr(command, 'search'):
            raise TypeError('command argument must be str or a regex')
        self.response_list.append((command, response))


    def load_command_handler_from_file(self, filename, autoprompt = True):
        """
        Wrapper around add_command_handler that reads the handlers from the
        file with the given name. The file is a Python script containing
        a list named 'commands' of tuples that map command names to
        handlers.

        @type  filename: str
        @param filename: The name of the file containing the tuples.
        @type  autoprompt: bool
        @param autoprompt: Whether to append a prompt to each response.
        """
        vars = {}
        execfile(filename, vars)
        commands = vars.get('commands')
        if not commands:
            raise Exception(filename + ' has no variable named "commands"')
        elif not hasattr(commands, '__iter__'):
            raise Exception(filename + ': "commands" has invalid type')
        for key, handler in commands:
            handler = self._create_autoprompt_handler(handler)
            self.add_command_handler(key, handler)

    def _connect_hook(self, hostname, port):
        assert self.connected_host is None
        self.connected_host = hostname
        self.connected_port = port or 0
        self.buffer         = ''

        if self.login_type == self.LOGIN_TYPE_PASSWORDONLY:
            self.prompt_stage = self.PROMPT_STAGE_PASSWORD
        elif self.login_type == self.LOGIN_TYPE_USERONLY:
            self.prompt_stage = self.PROMPT_STAGE_USERNAME
        elif self.login_type == self.LOGIN_TYPE_BOTH:
            self.prompt_stage = self.PROMPT_STAGE_USERNAME
        elif self.login_type == self.LOGIN_TYPE_NONE:
            self.prompt_stage = self.PROMPT_STAGE_CUSTOM
        else:
            assert False # No such login type.

        if self.banner is not None:
            self._say(self.banner + '\r\n')
        self._say(self._get_prompt())
        return True


    def _authenticate_hook(self, user, password, **kwargs):
        while 1:
            # Wait for the user prompt.
            #print 'Waiting for prompt'
            prompt  = [huawei_re,
                       login_fail_re,
                       cisco_user_re,
                       junos_user_re,
                       unix_user_re,
                       skey_re,
                       pass_re,
                       self.prompt_re]
            which    = None
            matches  = None
            response = None
            try:
                which, matches, response = self._expect_any(prompt)
            except:
                print 'Dummy.authenticate(): Error while waiting for prompt'
                raise

            # No match.
            if which < 0:
                if response is None:
                    response = ''
                msg = "Timeout while waiting for prompt. Buffer: %s" % repr(response)
                raise TransportException(msg)

            # Huawei welcome message.
            elif which == 0:
                self._dbg(1, "Huawei router detected.")
                self.remote_os = 'vrp'

            # Login error detected.
            elif which == 1:
                raise LoginFailure("Login failed")

            # User name prompt.
            elif which <= 4:
                self._dbg(1, "Username prompt %s received." % which)
                if self.remote_os == 'unknown':
                    self.remote_os = ('ios', 'junos', 'shell')[which - 2]
                self.send(user + '\r')
                if self.login_type == self.LOGIN_TYPE_USERONLY \
                  and not kwargs.get('wait'):
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            # s/key prompt.
            elif which == 5:
                self._dbg(1, "S/Key prompt received.")
                seq  = int(matches.group(1))
                seed = matches.group(2)
                self.last_tacacs_key_id = seq
                self._dbg(2, "Seq: %s, Seed: %s" % (seq, seed))
                phrase = otp(password, seed, seq)
                self._expect_any([pass_re])
                self.send(phrase + '\r')
                self._dbg(1, "Password sent.")
                if not kwargs.get('wait'):
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            # Cleartext password prompt.
            elif which == 6:
                self._dbg(1, "Cleartext password prompt received.")
                self.send(password + '\r')
                if not kwargs.get('wait'):
                    self._dbg(1, "Bailing out as requested.")
                    break
                continue

            # Shell prompt.
            elif which == 7:
                self._dbg(1, 'Shell prompt received.')
                self._examine_prompt(matches.group(0))
                self._dbg(1, 'Remote OS: %s' % self.remote_os)
                break

            else:
                assert 0 # Not reached.


    def _authorize_hook(self, password, **kwargs):
        # The username should not be asked, so not passed.
        return self._authenticate_hook('', password, **kwargs)


    def _examine_prompt(self, prompt):
        if iosxr_prompt_re.search(prompt):
            self.remote_os = 'ios_xr'


    def send(self, data):
        self._dbg(4, 'Sending %s' % repr(data))
        data = data.replace('\r', '\r\n')
        for command, response in self.response_list:
            if not command.search(data):
                continue
            if isinstance(response, str):
                self._say(data + response)
            else:
                self._say(data + response(data))
            return
        if self.strict and self.logged_in:
            raise Exception('Undefined command: ' + repr(data))
        prompt = self._get_prompt()
        self._say(data + prompt)


    def execute(self, data):
        # Send the command.
        self.send(data + '\r')
        return self.expect_prompt()


    def expect(self, prompt):
        # Wait for a prompt.
        try:
            res = self._expect_any([prompt])
            if res is None:
                self._dbg(2, "No prompt match")
                raise Exception('no match')
            result, match, self.response = res
        except:
            print 'Error while waiting for %s' % repr(prompt.pattern)
            raise

        if match:
            self._dbg(2, "Got a prompt, match was %s" % repr(match.group()))
            self._examine_prompt(match.group(0))
        self._dbg(5, "Response was %s" % repr(self.buffer))

        if result == -1 or self.buffer is None:
            error = 'Error while waiting for response from device'
            raise TransportException(error)

        self._examine_prompt(match.group(0))


    def close(self, force = False):
        self._say('\n')
        self.connected_host = None
        self.connected_port = None
