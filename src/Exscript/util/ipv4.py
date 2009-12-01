import socket, struct, math

def _least_bit(number):
    for n in range(0, 31):
        if number & (0x00000001l << n) != 0:
            return n + 1
    return 0

def _highest_bit(number):
    if number == 0:
        return 0
    number -= 1
    number |= number >> 1
    number |= number >> 2
    number |= number >> 4
    number |= number >> 8
    number |= number >> 16
    number += 1
    return math.sqrt(number)

def ip2int(ip):
    if ip == '255.255.255.255':
        return 0xFFFFFFFFl
    return struct.unpack('!L', socket.inet_aton(ip))[0]

def int2ip(number):
    return socket.inet_ntoa(struct.pack('!L', number))

def pfxlen2mask(pfxlen):
    return 0xFFFFFFFFl << (32 - int(pfxlen))

def mask2pfxlen(mask):
    mask_int = ip2int(mask)
    return 33 - _least_bit(mask_int)

def parse_prefix(prefix, default_mask = 24):
    if '/' in prefix:
        (network, pfxlen) = prefix.split('/')
    else:
        network = prefix
        pfxlen  = default_mask
    return ip2int(network), int(pfxlen)

def remote_ip(local_ip):
    local_ip = ip2int(local_ip)
    network  = local_ip & pfxlen2mask(30)
    return int2ip(network + 3 - (local_ip - network))
