from Exscriptd.config.AccountPoolConfig import AccountPoolConfig
from Exscriptd.config.DaemonConfig      import DaemonConfig
from Exscriptd.config.DatabaseConfig    import DatabaseConfig
from Exscriptd.config.ServiceConfig     import ServiceConfig
from Exscriptd.config.QueueConfig       import QueueConfig

modules = {
    'account-pool': AccountPoolConfig,
    'daemon':       DaemonConfig,
    'db':           DatabaseConfig,
    'service':      ServiceConfig,
    'queue':        QueueConfig
}
