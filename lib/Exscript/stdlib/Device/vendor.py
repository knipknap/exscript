import re

signature = [('self', 'integer')]

#FIXME: This function should really only call a show version parser that does
# all the heavy lifting and extracts more than just the vendor.
def execute(scope, force = 0):
    # If the vendor is cached, return it.
    vendor = scope.get('_stdlib.device.vendor')
    if vendor is not None and force == 0:
        return vendor

    # Find out the vendor.
    conn = scope.get('_connection')
    conn.execute('show version')
    for line in conn.response.split('\n')[1:]:
        match = re.match(r'^cisco', line)
        if match is not None:
            vendor = ['cisco']
        match = re.match(r'^JUNOS', line)
        if match is not None:
            vendor = ['juniper']

    # If it was still not found, return 'unknown'.
    if vendor is None:
        vendor = ['unknown']
    scope.define(**{'_stdlib.device.vendor': vendor})
    return vendor
