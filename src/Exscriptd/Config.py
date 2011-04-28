# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
import base64
import shutil
from lxml                    import etree
from Exscript                import Account, Queue, FileLogger
from Exscript.AccountPool    import AccountPool
from Exscript.util.file      import get_accounts_from_file
from Exscriptd.OrderDB       import OrderDB
from Exscriptd.HTTPDaemon    import HTTPDaemon
from Exscriptd.PythonService import PythonService
from Exscriptd.ConfigReader  import ConfigReader
from Exscriptd.util          import find_module_recursive
from Exscriptd.xml           import get_accounts_from_etree, \
                                    add_accounts_to_etree

default_config_dir = os.path.join('/etc', 'exscriptd')
default_logdir     = os.path.join('/var', 'log', 'exscriptd')

cache = {}
def cache_result(func):
    def wrapped(*args, **kwargs):
        key = func.__name__, repr(args), repr(kwargs)
        if key in cache:
            return cache[key]
        return func(*args, **kwargs)
    return wrapped

class Config(ConfigReader):
    def __init__(self,
                 cfg_dir           = default_config_dir,
                 resolve_variables = True):
        self.daemons       = {}
        self.cfg_dir       = cfg_dir
        self.service_dir   = os.path.join(cfg_dir, 'services')
        filename           = os.path.join(cfg_dir, 'main.xml')
        ConfigReader.__init__(self, filename, resolve_variables)
        self.logdir = self.cfgtree.findtext('logging/logdir', default_logdir)

    def _get_account_list_from_name(self, name):
        element = self.cfgtree.find('account-pool[@name="%s"]' % name)
        return get_accounts_from_etree(element)

    @cache_result
    def _init_account_pool_from_name(self, name):
        accounts = self._get_account_list_from_name(name)
        return AccountPool(accounts)

    @cache_result
    def _init_queue_from_name(self, name):
        # Create the queue first.
        logdir = os.path.join(self.logdir, 'queues', name)
        if not os.path.isdir(logdir):
            os.makedirs(logdir)
        element     = self.cfgtree.find('queue[@name="%s"]' % name)
        max_threads = element.find('max-threads').text
        delete_logs = element.find('delete-logs') is not None
        queue       = Queue(verbose = 0, max_threads = max_threads)
        logger      = FileLogger(logdir, 'a', delete_logs)
        self.loggers.append(logger) # needed to hold them alive

        # Assign account pools to the queue.
        for pool_elem in element.iterfind('account-pool'):
            pool = self._init_account_pool_from_name(pool_elem.text)
            cond = pool_elem.get('for')
            if cond is None:
                queue.add_account_pool(pool)
                continue

            condition = compile(cond, 'config', 'eval')
            def match_cb(host):
                return eval(condition, host.get_dict())
            queue.add_account_pool(pool, match_cb)

        return queue

    def _init_database_from_dbn(self, dbn):
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool
        #print 'Creating database connection for', dbn
        return create_engine(dbn, poolclass = NullPool)

    def _init_http_daemon(self, element):
        # Init the database for the daemon first, then
        # create the daemon (this does not start it).
        name    = element.get('name')
        address = element.find('address').text or ''
        port    = int(element.find('port').text)
        db_elem = element.find('database')
        if db_elem is None:
            engine = self._init_database_from_dbn(':memory:')
        else:
            engine = self.get_database_from_name(db_elem.text)
        db = OrderDB(engine)
        #print 'Initializing database tables...'
        db.install()
        logdir = os.path.join(self.logdir, 'daemons', name)
        if not os.path.isdir(logdir):
            os.makedirs(logdir)
        daemon = HTTPDaemon(name, db, logdir, address, port)

        # Add some accounts, if any.
        account_pool = element.find('account-pool')
        for account in self._get_account_list_from_name(account_pool.text):
            daemon.add_account(account)

        return daemon

    def _init_daemons(self):
        for element in self.cfgtree.iterfind('daemon'):
            name = element.get('name')
            self.get_daemon_from_name(name)

    def _get_service_files(self):
        """
        Searches the config directory for service configuration files,
        and returns a list of path names.
        """
        files = []
        for file in os.listdir(self.service_dir):
            config_dir = os.path.join(self.service_dir, file)
            if not os.path.isdir(config_dir):
                continue
            config_file = os.path.join(config_dir, 'config.xml')
            if not os.path.isfile(config_file):
                continue
            files.append(config_file)
        return files

    def _get_service_file_from_name(self, name):
        """
        Searches the config directory for service configuration files,
        and returns the name of the first file that defines a service
        with the given name.
        """
        for file in self._get_service_files():
            xml     = etree.parse(file)
            element = xml.find('service[@name="%s"]' % name)
            if element is not None:
                return file
        return None

    def _init_service(self, filename):
        service_dir = os.path.dirname(filename)
        cfgtree     = ConfigReader(filename).cfgtree
        for element in cfgtree.iterfind('service'):
            name = element.get('name')
            print 'Loading service "%s"...' % name

            module      = element.find('module').text
            daemon_name = element.find('daemon').text
            daemon      = self.get_daemon_from_name(daemon_name)
            queue_elem  = element.find('queue')
            queue_name  = queue_elem is not None and queue_elem.text
            queue       = self._init_queue_from_name(queue_name)
            service     = PythonService(daemon,
                                        name,
                                        module,
                                        service_dir,
                                        self,
                                        queue = queue)
            daemon.add_service(name, service)
            print 'Service "%s" initialized.' % name

    def _init_services(self):
        for file in self._get_service_files():
            service = self._init_service(file)

    def has_account_pool(self, name):
        return self.cfgtree.find('account-pool[@name="%s"]' % name) is not None

    def add_account_pool_from_file(self, name, filename):
        # Remove the pool if it exists.
        xml       = self.cfgtree.getroot()
        pool_elem = xml.find('account-pool[@name="%s"]' % name)
        if pool_elem is not None:
            xml.remove(pool_elem)

        # Import the new pool from the given file.
        pool_elem = etree.SubElement(xml, 'account-pool', name = name)
        accounts  = get_accounts_from_file(filename)
        add_accounts_to_etree(pool_elem, accounts)

        self.save()

    def has_queue(self, name):
        return self.cfgtree.find('queue[@name="%s"]' % name) is not None

    def has_database(self, name):
        return self.cfgtree.find('database[@name="%s"]' % name) is not None

    def add_database(self, db_name, dbn):
        # Create an XML segment for the database.
        changed = False
        xml     = self.cfgtree.getroot()
        db_elem = xml.find('database[@name="%s"]' % db_name)
        if db_elem is None:
            changed = True
            db_elem = etree.SubElement(xml, 'database', name = db_name)

        # Add the dbn the the XML.
        if self._add_or_update_elem(db_elem, 'dbn', dbn):
            changed = True

        # Write the resulting XML.
        if not changed:
            return False
        self.save()
        return True

    @cache_result
    def get_database_from_name(self, name):
        element = self.cfgtree.find('database[@name="%s"]' % name)
        dbn     = element.find('dbn').text
        return self._init_database_from_dbn(dbn)

    def add_queue(self,
                  queue_name,
                  account_pool,
                  max_threads,
                  delete_logs):
        # Create an XML segment for the queue.
        changed    = False
        xml        = self.cfgtree.getroot()
        queue_elem = xml.find('queue[@name="%s"]' % queue_name)
        if queue_elem is None:
            changed    = True
            queue_elem = etree.SubElement(xml, 'queue', name = queue_name)

        # Create an XML reference to the account pool.
        acc_elem = queue_elem.find('account-pool')
        if account_pool is None and acc_elem is not None:
            changed = True
            queue_elem.remove(acc_elem)
        elif account_pool is not None:
            try:
                self._init_account_pool_from_name(account_pool)
            except AttributeError:
                raise Exception('no such account pool: %s' % account_pool)

            if self._add_or_update_elem(queue_elem,
                                        'account-pool',
                                        account_pool):
                changed = True

        # Define the number of threads.
        if self._add_or_update_elem(queue_elem, 'max-threads', max_threads):
            changed = True

        # Set the delete-logs flag.
        delete_logs_elem = queue_elem.find('delete-logs')
        has_flag         = delete_logs_elem is not None
        if has_flag and not delete_logs:
            changed = True
            queue_elem.remove(delete_logs_elem)
        elif delete_logs and not has_flag:
            changed = True
            etree.SubElement(queue_elem, 'delete-logs')

        if not changed:
            return False

        # Write the resulting XML.
        self.save()
        return True

    def has_service(self, service_name):
        return self._get_service_file_from_name(service_name) is not None

    def add_service(self,
                    service_name,
                    module_name = None,
                    daemon_name = None,
                    queue_name  = None):
        pathname = self._get_service_file_from_name(service_name)
        changed  = False

        if not pathname:
            if not module_name:
                raise Exception('module name is required')

            # Find the installation path of the module.
            file, module_path, desc = find_module_recursive(module_name)

            # Create a directory for the new service, if it does not
            # already exist.
            service_dir = os.path.join(self.service_dir, service_name)
            if not os.path.isdir(service_dir):
                os.makedirs(service_dir)

            # Copy the default config file.
            cfg_file = os.path.join(module_path, 'config.xml.tmpl')
            pathname = os.path.join(service_dir, 'config.xml')
            if not os.path.isfile(pathname):
                shutil.copy(cfg_file, pathname)
            changed = True

        # Create an XML segment for the service.
        doc         = etree.parse(pathname)
        xml         = doc.getroot()
        service_ele = xml.find('service[@name="%s"]' % service_name)
        if service_ele is None:
            changed = True
            service_ele = etree.SubElement(xml, 'service', name = service_name)

        # By default, use the first daemon defined in the main config file.
        if daemon_name is None:
            daemon_name = self.cfgtree.find('daemon').get('name')
        if self._add_or_update_elem(service_ele, 'daemon', daemon_name):
            changed = True

        # Add an XML statement pointing to the module.
        if module_name is not None:
            if self._add_or_update_elem(service_ele, 'module', module_name):
                changed = True

        # By default, use the first queue defined in the main config file.
        if queue_name is None:
            queue_name = self.cfgtree.find('queue').get('name')
        if not self.has_queue(queue_name):
            raise Exception('no such queue: ' + queue_name)
        if self._add_or_update_elem(service_ele, 'queue', queue_name):
            changed = True

        if not changed:
            return False

        # Write the resulting XML.
        self._write_xml(xml, pathname)
        return True

    def _get_service_var_elem(self, service_name):
        pathname = self._get_service_file_from_name(service_name)
        doc      = etree.parse(pathname)
        xml      = doc.getroot()
        return pathname, xml, xml.find('variables')

    def set_service_variable(self, service_name, varname, value):
        path, xml, var_elem = self._get_service_var_elem(service_name)
        elem                = var_elem.find(varname)
        if elem is None:
            elem = etree.SubElement(var_elem, varname)
        elem.text = value
        self._write_xml(xml, path)

    def unset_service_variable(self, service_name, varname):
        path, xml, var_elem = self._get_service_var_elem(service_name)
        elem                = var_elem.find(varname)
        if elem is not None:
            var_elem.remove(elem)
        self._write_xml(xml, path)

    def has_daemon(self, name):
        return self.cfgtree.find('daemon[@name="%s"]' % name) is not None

    def add_daemon(self,
                   name,
                   address,
                   port,
                   account_pool,
                   database):
        daemon_elem = self.cfgtree.find('daemon[@name="%s"]' % name)
        changed     = False
        if daemon_elem is None:
            changed     = True
            daemon_elem = etree.SubElement(self.cfgtree.getroot(),
                                           'daemon',
                                           type = 'http',
                                           name = name)

        if self._add_or_update_elem(daemon_elem, 'address', address):
            changed = True
        if self._add_or_update_elem(daemon_elem, 'port', port):
            changed = True
        if self._add_or_update_elem(daemon_elem, 'account-pool', account_pool):
            changed = True
        if self._add_or_update_elem(daemon_elem, 'database', database):
            changed = True

        if not changed:
            return False
        self.save()
        return changed

    def get_daemon_from_name(self, name):
        if name in self.daemons:
            return self.daemons[name]

        # Create the daemon.
        element = self.cfgtree.find('daemon[@name="%s"]' % name)
        type    = element.get('type')
        if type == 'http':
            daemon = self._init_http_daemon(element)
        else:
            raise Exception('No such daemon type: %s' % type)

        self.daemons[name] = daemon
        return daemon

    def get_daemons(self):
        self._init_daemons()
        self._init_services()
        return self.daemons.values()
