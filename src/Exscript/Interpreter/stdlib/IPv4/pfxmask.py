import util

def execute(scope, ips, pfxlens):
    mask   = util.pfxlen2mask(pfxlens[0])
    result = []
    for ip in ips:
        ip = util.ip2int(ip)
        result.append(util.int2ip(ip & mask))
    return result
