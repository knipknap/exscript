#!/usr/bin/env python
import os, base64, re
from sqlalchemy     import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from Order          import Order
from Database       import Base
from lxml           import etree
from Exscript       import Account, Queue
from INotifyDaemon  import INotifyDaemon
from PythonService  import PythonService
from util           import resolve_variables

class Config(object):
    def __init__(self, filename):
        self.cfgtree   = etree.parse(filename)
        self.variables = {}
        self.queues    = {}
        self._clean_tree()

    def _resolve(self, text):
        if text is None:
            return None
        return resolve_variables(self.variables, text.strip())

    def _clean_tree(self):
        # Read all variables.
        for element in self.cfgtree.iterfind('variables'):
            varname = element.tag.strip()
            value   = resolve_variables(self.variables, element.text)
            self.variables[varname] = value

        # Resolve variables everywhere.
        for element in self.cfgtree.iter():
            element.text = self._resolve(element.text)
            for attr in element.attrib:
                value                = element.attrib[attr]
                element.attrib[attr] = self._resolve(value)

    def init_account_pool_from_name(self, name):
        accounts = []
        element  = self.cfgtree.find('account-pool[@name="%s"]' % name)
        for child in element.iterfind('account'):
            user     = child.find('user').text
            password = child.find('password').text
            accounts.append(Account(user, base64.decodestring(password)))
        return accounts

    def init_queue_from_name(self, name):
        if self.queues.has_key(name):
            return self.queues[name]

        # Create the queue first.
        element     = self.cfgtree.find('queue[@name="%s"]' % name)
        max_threads = element.find('max-threads').text
        logdir      = element.find('logdir').text
        delete_logs = element.find('delete-logs') is not None
        if not os.path.isdir(logdir):
            os.makedirs(logdir)
        queue = Queue(verbose     = 0,
                      max_threads = max_threads,
                      logdir      = logdir,
                      delete_logs = delete_logs)

        # Add some accounts, if any.
        account_pool = element.find('account-pool')
        if account_pool is not None:
            accounts = self.init_account_pool_from_name(account_pool.text)
            queue.add_account(accounts)

        self.queues[name] = queue
        return queue

    def init_database_from_name(self, name):
        element = self.cfgtree.find('database[@name="%s"]' % name)
        dbn     = element.find('dbn').text
        print 'Creating database connection for', dbn
        engine  = create_engine(dbn)
        Session = scoped_session(sessionmaker(bind = engine))
        print 'Initializing database tables...'
        Base.metadata.create_all(engine)
        return Session

    def init_service_from_name(self,
                               daemon,
                               name,
                               filename,
                               queue = None):
        print 'Loading service "%s"...' % name,
        cfgtree = etree.parse(filename)
        dirname = os.path.dirname(filename)
        element = cfgtree.find('service')
        type    = element.get('type')

        if type == 'python':
            basename  = element.get('filename')
            filename  = os.path.join(dirname, basename)
            autoqueue = element.find('autoqueue') is not None
            service   = PythonService(daemon,
                                      name,
                                      filename,
                                      queue     = queue,
                                      autoqueue = autoqueue)
        else:
            raise Exception('Invalid service type: %s' % type)
        print 'done.'
        return service

    def init_inotify_daemon(self, element):
        # Init the database for the daemon first, then
        # create the daemon (this does not start it).
        name      = element.get('name')
        directory = element.find('directory').text
        db_name   = element.find('database').text
        db        = self.init_database_from_name(db_name)
        daemon    = INotifyDaemon(name, directory = directory, database = db)

        # Load any associated services from external xml files.
        for service in element.iterfind('load-service'):
            name       = service.get('name')
            path       = service.get('path')
            queue_elem = service.find('queue')
            queue_name = queue_elem is not None and queue_elem.text
            queue      = self.init_queue_from_name(queue_name)
            service    = self.init_service_from_name(daemon,
                                                     name,
                                                     path,
                                                     queue = queue)
            daemon.add_service(name, service)

        return daemon

    def init_daemon_from_name(self, name):
        # Create the daemon.
        element = self.cfgtree.find('daemon[@name="%s"]' % name)
        type    = element.get('type')
        if type == 'inotify':
            return self.init_inotify_daemon(element)
        else:
            raise Exception('No such daemon type: %s' % type)

    def init_daemons(self):
        daemons = []
        for element in self.cfgtree.iterfind('daemon'):
            name   = element.get('name')
            daemon = self.init_daemon_from_name(name)
            daemons.append(daemon)
        return daemons

    def get_inotify_daemon_dir(self, daemon_name):
        daemon = self.cfgtree.find('daemon[@name="%s"]' % daemon_name)
        return daemon.find('directory').text

    def get_inotify_daemon_db_name(self, daemon_name):
        daemon = self.cfgtree.find('daemon[@name="%s"]' % daemon_name)
        return daemon.find('database').text
