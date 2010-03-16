class Order(object):
    def __init__(self, service_name, hosts):
        self.service_name = service_name
        self.hosts        = hosts

    def add_host(self, host):
        self.hosts.append(host)
