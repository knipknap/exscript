import socket, struct

def ip2int(ip):
    return struct.unpack('L', socket.inet_aton(ip))[0]

def int2ip(number):
    return socket.inet_ntoa(struct.pack('L', number))

def pfxlen2mask(pfxlen):
    return 0xFFFFFFFFl << (32 - int(pfxlen))

def parse_prefix(prefix, default_mask = 24):
    if '/' in prefix:
        (network, pfxlen) = prefix.split('/')
    else:
        network = prefix
        pfxlen  = default_mask
    return (ip2int(network), int(pfxlen))
