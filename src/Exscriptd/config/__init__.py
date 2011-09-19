from Exscriptd.config.AccountPoolConfig import AccountPoolConfig
from Exscriptd.config.BaseConfig        import BaseConfig
from Exscriptd.config.DaemonConfig      import DaemonConfig
from Exscriptd.config.DatabaseConfig    import DatabaseConfig
from Exscriptd.config.ServiceConfig     import ServiceConfig
from Exscriptd.config.QueueConfig       import QueueConfig

modules = {
    'account-pool': AccountPoolConfig,
    'base':         BaseConfig,
    'daemon':       DaemonConfig,
    'db':           DatabaseConfig,
    'service':      ServiceConfig,
    'queue':        QueueConfig
}
