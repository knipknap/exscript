from AccountPoolConfig import AccountPoolConfig
from DaemonConfig      import DaemonConfig
from DatabaseConfig    import DatabaseConfig
from ServiceConfig     import ServiceConfig
from QueueConfig       import QueueConfig

modules = {
    'account-pool': AccountPoolConfig,
    'daemon':       DaemonConfig,
    'db':           DatabaseConfig,
    'service':      ServiceConfig,
    'queue':        QueueConfig
}
