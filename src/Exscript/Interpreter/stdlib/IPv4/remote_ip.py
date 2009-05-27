import util

def execute(scope, local_ips):
    return [util.remote_ip(ip) for ip in local_ips]
