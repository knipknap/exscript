#!/usr/bin/env python
import os, base64, re
from sqlalchemy     import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from Order          import Order
from Database       import Base
from lxml           import etree
from Exscript       import Account, Queue
from INotifyDaemon  import INotifyDaemon
from Service        import Service
from Task           import Task
from util           import resolve_variables

class Config(object):
    def __init__(self, filename):
        self.cfgtree   = etree.parse(filename)
        self.variables = {}
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

    def _collect_task_children(self, cfgtree, element, dirname):
        children = []
        for child in element:
            if child.tag in ('connect', 'autologin'):
                children.append((child.tag,))
            elif child.tag in ('sendline', 'execline'):
                children.append((child.tag, child.text))
            elif child.tag in ('expect', 'set-prompt'):
                regex = re.compile(child.text)
                children.append((child.tag, regex))
            elif child.tag == 'invoke-task':
                name = child.get('name').strip()
                task = self._init_task_from_name(cfgtree, name, dirname)
                args = dict((c.tag, c.text.strip()) for c in child)
                children.append((child.tag, task, args))
            elif child.tag == 'invoke-script':
                language = child.get('language').strip()
                filename = os.path.join(dirname, child.text.strip())
                if not os.path.isfile(filename):
                    raise Exception('not a valid file: ' + filename)
                if language == 'python':
                    content          = open(filename).read()
                    code             = compile(content, filename, 'exec')
                    vars             = globals().copy()
                    vars['__file__'] = filename
                    result           = eval(code, vars)
                    start            = vars.get('run')
                    if not start:
                        msg = 'Error: %s run() function not found' % filename
                        raise Exception(msg)
                    children.append(('invoke-python', start))
                else:
                    raise Exception('Unsupported language %s.' % language)
            else:
                raise Exception('Invalid tag %s' % child.tag)
        return children

    def _init_task_from_name(self, cfgtree, name, dirname):
        element = cfgtree.find('task[@name="%s"]' % name)
        actions = self._collect_task_children(cfgtree, element, dirname)
        return Task(name, actions)

    def init_service_from_name(self, name, filename):
        print 'Loading service "%s"...' % name,
        cfgtree = etree.parse(filename)
        dirname = os.path.dirname(filename)
        element = cfgtree.find('service')
        actions = self._collect_task_children(cfgtree, element, dirname)
        service = Service(name, actions)
        print 'done.'
        return service

    def init_inotify_daemon(self, element):
        name       = element.get('name')
        directory  = element.find('directory').text
        queue_name = element.find('queue').text
        queue      = self.init_queue_from_name(queue_name)
        db_name    = element.find('database').text
        db         = self.init_database_from_name(db_name)

        services = {}
        for service in element.iterfind('load-service'):
            name           = service.get('name')
            path           = service.get('path')
            services[name] = self.init_service_from_name(name, path)

        return INotifyDaemon(name,
                             directory = directory,
                             database  = db,
                             queue     = queue,
                             services  = services)

    def init_daemon_from_name(self, name):
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
