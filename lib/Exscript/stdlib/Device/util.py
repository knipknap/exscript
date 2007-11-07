import re

def update_host_info(scope, force = 0):
    # If the info is cached, return it.
    info = scope.get('_stdlib.device.have_remote_info')
    if info is not None and force == 0:
        return
    scope.define(**{'_stdlib.device.have_remote_info': 1})

    conn = scope.get('_connection')
    conn.execute('show version')
    for line in conn.response.split('\n')[1:]:
        if re.match(r'^JUNOS', line, re.I) is not None:
            conn.remote_info['os']     = 'junos'
            conn.remote_info['vendor'] = 'juniper'
            break
        match = re.match(r'^Cisco IOS XR', line, re.I)
        if match is not None:
            conn.remote_info['os']     = 'ios_xr'
            conn.remote_info['vendor'] = 'cisco'
            break
        if re.match(r'^cisco', line, re.I) is not None:
            conn.remote_info['os']     = 'ios'
            conn.remote_info['vendor'] = 'cisco'
            break
