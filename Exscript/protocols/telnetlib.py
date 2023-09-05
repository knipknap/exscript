"""Telnetlib extension to work with Exscript"""
import sys
import telnetlib as tn

import selectors

# poll/select have the advantage of not requiring any extra file descriptor,
# contrarily to epoll/kqueue (also, they require a single syscall).
if hasattr(selectors, 'PollSelector'):
    _TelnetSelector = selectors.PollSelector
else:
    _TelnetSelector = selectors.SelectSelector


class Telnet(tn.Telnet):

    def __init__(self, host=None, port=0, encoding='latin1', **kwargs):
        self.encoding = encoding
        self.connect_timeout = kwargs.pop('connect_timeout', None)
        self.window_size = kwargs.pop('termsize')
        self.stdout = kwargs.pop('stdout', sys.stdout)
        self.stderr = kwargs.pop('stderr', sys.stderr)
        self.termtype = kwargs.pop('termtype', 'dumb')
        self.data_callback = kwargs.pop('receive_callback', None)
        super().__init__(host=host, port=port, **kwargs)
        self.cookedq = ''


    def waitfor(self, relist, timeout=None, cleanup=None):
        """Wait for any re in relist to match in the response.

        Args:
            relist (_type_): List of regular expressions to match.
            timeout (int, optional): Connection timeout. Defaults to None.
            cleanup (boolean, optional): Not used anymore. Exists for legacy.

        Returns:
           Return a tuple of three items: the index in the list of the
            first regular expression that matches; the match object
            returned; and the text read up till and including the match.
        """
        return super().expect(list=relist, timeout=timeout)


    def expect(self, relist, timeout=None, cleanup=None):
        """
        Like waitfor(), but removes the matched data from the incoming
        buffer.
        """
        index, match, data = self.waitfor(relist, timeout=timeout)
        return index, match, relist[index].sub("", data)


    def process_rawq(self):
        """Transfer from raw queue to cooked queue.

        Set self.eof when connection is closed.  Don't block unless in
        the midst of an IAC sequence.

        """
        buf = [b'', b'']
        try:
            while self.rawq:
                c = self.rawq_getchar()
                if not self.iacseq:
                    if c == tn.theNULL:
                        continue
                    if c == b"\021":
                        continue
                    if c != tn.IAC:
                        buf[self.sb] = buf[self.sb] + c
                        continue
                    else:
                        self.iacseq += c
                elif len(self.iacseq) == 1:
                    # 'IAC: IAC CMD [OPTION only for WILL/WONT/DO/DONT]'
                    if c in (tn.DO, tn.DONT, tn.WILL, tn.WONT):
                        self.iacseq += c
                        continue

                    self.iacseq = b''
                    if c == tn.IAC:
                        buf[self.sb] = buf[self.sb] + c
                    else:
                        if c == tn.SB: # SB ... SE start.
                            self.sb = 1
                            self.sbdataq = b''
                        elif c == tn.SE:
                            self.sb = 0
                            self.sbdataq = self.sbdataq + buf[1]
                            buf[1] = b''
                        if self.option_callback:
                            # Callback is supposed to look into
                            # the sbdataq
                            self.option_callback(self.sock, c, tn.NOOPT)
                        else:
                            # We can't offer automatic processing of
                            # suboptions. Alas, we should not get any
                            # unless we did a WILL/DO before.
                            self.msg('IAC %d not recognized' % ord(c))
                elif len(self.iacseq) == 2:
                    cmd = self.iacseq[1:2]
                    self.iacseq = b''
                    opt = c
                    if cmd in (tn.DO, tn.DONT):
                        self.msg('IAC %s %d',
                            cmd == tn.DO and 'DO' or 'DONT', ord(opt))
                        if self.option_callback:
                            self.option_callback(self.sock, cmd, opt)
                        else:
                            self.sock.sendall(tn.IAC + tn.WONT + opt)
                    elif cmd in (tn.WILL, tn.WONT):
                        self.msg('IAC %s %d',
                            cmd == tn.WILL and 'WILL' or 'WONT', ord(opt))
                        if self.option_callback:
                            self.option_callback(self.sock, cmd, opt)
                        else:
                            self.sock.sendall(tn.IAC + tn.DONT + opt)
        except EOFError: # raised by self.rawq_getchar()
            self.iacseq = b'' # Reset on EOF
            self.sb = 0
        self.cookedq = self.cookedq + buf[0].decode(self.encoding)
        self.sbdataq = self.sbdataq + buf[1].decode(self.encoding)


    def listener(self):
        """Helper for mt_interact() -- this executes in the other thread."""
        while 1:
            try:
                data = self.read_eager()
            except EOFError:
                print('*** Connection closed by remote host ***')
                return
            if data:
                self.stdout.write(data.decode('ascii'))
            else:
                self.stdout.flush()


    def interact(self):
        """Interaction function, emulates a very dumb telnet client."""
        if sys.platform == "win32":
            self.mt_interact()
            return
        with _TelnetSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            selector.register(sys.stdin, selectors.EVENT_READ)

            while True:
                for key, events in selector.select():
                    if key.fileobj is self:
                        try:
                            text = self.read_eager()
                        except EOFError:
                            print('*** Connection closed by remote host ***')
                            return
                        if text:
                            self.stdout.write(text.decode('ascii'))
                            self.stdout.flush()
                    elif key.fileobj is sys.stdin:
                        line = sys.stdin.readline().encode('ascii')
                        if not line:
                            return
                        self.write(line)