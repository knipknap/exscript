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
from Order                   import Order
from OrderDB                 import OrderDB
from lxml                    import etree
from Exscript                import Account, Queue
from HTTPDaemon              import HTTPDaemon
from PythonService           import PythonService
from ConfigReader            import ConfigReader
from Exscript.AccountManager import AccountManager
from util                    import find_module_recursive
from Exscript.util.file      import get_accounts_from_file

default_config_dir = os.path.join('/etc', 'exscriptd')

class Config(ConfigReader):
    def __init__(self,
                 cfg_dir           = default_config_dir,
                 resolve_variables = True):
        self.daemons          = {}
        self.account_managers = {}
        self.queues           = {}
        self.cfg_dir          = cfg_dir
        self.service_dir      = os.path.join(cfg_dir, 'services')
        filename              = os.path.join(cfg_dir, 'main.xml')
        ConfigReader.__init__(self, filename, resolve_variables)

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
        for account in get_accounts_from_file(filename):
            b64password = base64.encodestring(account.get_password())
            acc_elem    = etree.SubElement(pool_elem, 'account')
            etree.SubElement(acc_elem, 'user').text = account.get_name()
            etree.SubElement(acc_elem, 'password').text = b64password

        self.save()

    def init_account_pool_from_name(self, name):
        accounts = []
        element  = self.cfgtree.find('account-pool[@name="%s"]' % name)
        for child in element.iterfind('account'):
            user     = child.find('user').text
            password = child.find('password').text
            accounts.append(Account(user, base64.decodestring(password)))
        return accounts

    def init_account_manager_from_name(self, name):
        if self.account_managers.has_key(name):
            return self.account_managers[name]
        accounts = self.init_account_pool_from_name(name)
        manager  = AccountManager(accounts)
        self.account_managers[name] = manager
        return manager

    def has_queue(self, name):
        return self.cfgtree.find('queue[@name="%s"]' % name) is not None

    def init_queue_from_name(self, name, logdir):
        if self.queues.has_key(name):
            return self.queues[name]

        # Create the queue first.
        element     = self.cfgtree.find('queue[@name="%s"]' % name)
        max_threads = element.find('max-threads').text
        delete_logs = element.find('delete-logs') is not None
        queue       = Queue(verbose     = 0,
                            max_threads = max_threads,
                            logdir      = logdir,
                            delete_logs = delete_logs)

        # Add some accounts, if any.
        account_pool = element.find('account-pool')
        if account_pool is not None:
            manager = self.init_account_manager_from_name(account_pool.text)
            queue.account_manager = manager

        self.queues[name] = queue
        return queue

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

    def init_database_from_dbn(self, dbn):
        from sqlalchemy import create_engine
        #print 'Creating database connection for', dbn
        engine  = create_engine(dbn)
        db      = OrderDB(engine)
        #print 'Initializing database tables...'
        db.install()
        return db

    def init_database_from_name(self, name):
        element = self.cfgtree.find('database[@name="%s"]' % name)
        dbn     = element.find('dbn').text
        return self.init_database_from_dbn()

    def load_service(self, filename):
        service_dir = os.path.dirname(filename)
        cfgtree     = ConfigReader(filename).cfgtree
        for element in cfgtree.iterfind('service'):
            name = element.get('name')
            print 'Loading service "%s"...' % name,

            module      = element.find('module').text
            daemon_name = element.find('daemon').text
            daemon      = self.init_daemon_from_name(daemon_name)
            queue_elem  = element.find('queue')
            queue_name  = queue_elem is not None and queue_elem.text
            logdir      = daemon.get_logdir()
            queue       = self.init_queue_from_name(queue_name, logdir)
            service     = PythonService(daemon,
                                        name,
                                        module,
                                        service_dir,
                                        queue = queue)
            daemon.add_service(name, service)
            print 'done.'

    def get_service_files(self):
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

    def get_service_file_from_name(self, name):
        for file in self.get_service_files():
            xml     = etree.parse(file)
            element = xml.find('service[@name="%s"]' % name)
            if element is not None:
                return file
        return None

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
                self.init_account_pool_from_name(account_pool)
            except AttributeError:
                raise Exception('no such account pool: %s' % account_pool)

            self._add_or_update_elem(queue_elem, 'account-pool', account_pool)

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
        return self.get_service_file_from_name(service_name) is not None

    def add_service(self,
                    service_name,
                    module_name = None,
                    daemon_name = None,
                    queue_name  = None):
        pathname = self.get_service_file_from_name(service_name)
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
        pathname = self.get_service_file_from_name(service_name)
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

    def load_services(self):
        for file in self.get_service_files():
            service = self.load_service(file)

    def has_daemon(self, name):
        return self.cfgtree.find('daemon[@name="%s"]' % name) is not None

    def add_daemon(self,
                   name,
                   address,
                   port,
                   logdir,
                   account_pool,
                   database):
        daemon_elem = self.cfgtree.find('daemon[@name="%s"]' % name)
        changed     = False
        if daemon_elem is None:
            changed     = True
            daemon_elem = etree.SubElement(self.cfgtree.getroot(),
                                           'daemon',
                                           type = 'rest',
                                           name = name)

        if self._add_or_update_elem(daemon_elem, 'address', address):
            changed = True
        if self._add_or_update_elem(daemon_elem, 'port', port):
            changed = True
        if self._add_or_update_elem(daemon_elem, 'logdir', logdir):
            changed = True
        if self._add_or_update_elem(daemon_elem, 'account-pool', account_pool):
            changed = True
        if self._add_or_update_elem(daemon_elem, 'database', database):
            changed = True

        if not changed:
            return False
        self.save()
        return changed

    def init_rest_daemon(self, element):
        # Init the database for the daemon first, then
        # create the daemon (this does not start it).
        name    = element.get('name')
        address = element.findtext('address', '')
        port    = int(element.find('port').text)
        db_name = element.find('database')
        logdir  = element.find('logdir').text
        if db_elem is None:
            db = self.database_from_dbn(':memory:')
        else:
            db = self.init_database_from_name(db_elem.text)
        if not os.path.isdir(logdir):
            os.makedirs(logdir)
        daemon  = HTTPDaemon(name,
                             address,
                             port,
                             database = db,
                             logdir   = logdir)

        # Add some accounts, if any.
        account_pool = element.find('account-pool')
        for account in self.init_account_pool_from_name(account_pool.text):
            daemon.add_account(account)

        return daemon

    def init_daemon_from_name(self, name):
        if self.daemons.has_key(name):
            return self.daemons[name]

        # Create the daemon.
        element = self.cfgtree.find('daemon[@name="%s"]' % name)
        type    = element.get('type')
        if type == 'rest':
            daemon = self.init_rest_daemon(element)
        else:
            raise Exception('No such daemon type: %s' % type)

        self.daemons[name] = daemon
        return daemon

    def init_daemons(self):
        self.load_services()
        return self.daemons.values()
