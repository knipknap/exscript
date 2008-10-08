import util

def execute(scope, prefixes, destination, default_mask = [24]):
    needle = util.ip2int(destination[0])
    for prefix in prefixes:
        (network, pfxlen) = util.parse_prefix(prefix, default_mask[0])
        mask              = util.pfxlen2mask(pfxlen)
        if needle & mask == network & mask:
            return [1]
    return [0]
