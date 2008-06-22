import util

def execute(scope, ips, mask):
    mask   = util.ip2int(mask[0])
    result = []
    for ip in ips:
        ip = ip2int(ip)
        result.append(int2ip(ip & mask))
    return result
