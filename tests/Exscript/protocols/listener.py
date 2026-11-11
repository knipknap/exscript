"""
Listening sockets for the servers of the tests.
"""

import errno
import socket


def listen(host='127.0.0.1', family=socket.AF_INET):
    """
    Returns a socket that listens on a free port of the given address, like
    Exscript.servers.Server.start() on port 0: without SO_REUSEADDR, unlike
    socket.create_server(), and if the port that the system chose is in
    use, e.g. on the Windows host of WSL, to which WSL forwards its ports,
    on another one.
    """
    attempts = 5
    while True:
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.bind((host, 0))
            sock.listen()
            return sock
        except OSError as e:
            sock.close()
            attempts -= 1
            if e.errno != errno.EADDRINUSE or not attempts:
                raise
