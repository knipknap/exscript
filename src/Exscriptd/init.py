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

def _read_variables(cfgtree):
    variables = {}
    for element in cfgtree.iterfind('variables'):
        varname = element.tag.strip()
        value   = element.text.strip()
        variables[varname] = resolve_variables(variables, value)
    return variables

def _read_account_pool(cfgtree, variables):
    accounts = []
    for element in cfgtree.iterfind('account'):
        user     = element.find('user').text.strip()
        user     = resolve_variables(variables, user)
        password = element.find('password').text.strip()
        accounts.append(Account(user, base64.decodestring(password)))
    return accounts

def _read_account_pools(cfgtree, variables):
    pools = {}
    for element in cfgtree.iterfind('account-pool'):
        name        = element.get('name').strip()
        name        = resolve_variables(variables, name)
        pools[name] = _read_account_pool(element, variables)
    return pools

def _read_file_store(element, variables):
    dirname = element.find('basedir').text.strip()
    dirname = resolve_variables(variables, dirname)
    return FileStore(dirname)

def _read_gelatin(element, variables):
    dirname = element.find('syntax-dir').text.strip()
    dirname = resolve_variables(variables, dirname)
    return GelatinProcessor(dirname)

def _read_xslt(element, variables):
    return XsltProcessor()

def _read_existdb(element, variables):
    host       = element.find('host').text.strip()
    host       = resolve_variables(variables, host)
    port       = element.find('port').text.strip()
    port       = resolve_variables(variables, port)
    user       = element.find('user').text.strip()
    user       = resolve_variables(variables, user)
    password   = element.find('password').text.strip()
    collection = element.find('collection').text.strip()
    collection = resolve_variables(variables, collection)
    return ExistDBStore(host       = host,
                        port       = port,
                        user       = user,
                        password   = password,
                        collection = collection)

def _read_queue(element, variables, accounts):
    max_threads  = element.find('max-threads').text.strip()
    max_threads  = resolve_variables(variables, max_threads)
    logdir       = element.find('logdir').text.strip()
    logdir       = resolve_variables(variables, logdir)
    delete_logs  = element.find('delete-logs') is not None
    account_pool = element.find('account-pool').text.strip()
    account_pool = resolve_variables(variables, account_pool)
    if not os.path.isdir(logdir):
        os.makedirs(logdir)
    queue = Queue(verbose     = 0,
                  max_threads = max_threads,
                  logdir      = logdir,
                  delete_logs = delete_logs)
    queue.add_account(accounts[account_pool])
    return queue

def _read_queues(cfgtree, variables, accounts):
    queues = {}
    for element in cfgtree.iterfind('queue'):
        name         = element.get('name').strip()
        name         = resolve_variables(variables, name)
        queues[name] = _read_queue(element, variables, accounts)
    return queues

def _read_database(element, variables):
    dbn = element.find('dbn').text.strip()
    dbn = resolve_variables(variables, dbn)

    print 'Creating database connection for', dbn
    engine  = create_engine(dbn)
    Session = scoped_session(sessionmaker(bind = engine))
    print 'Initializing database tables...'
    Base.metadata.create_all(engine)
    return Session

def _read_databases(cfgtree, variables):
    databases = {}
    for element in cfgtree.iterfind('database'):
        name            = element.get('name').strip()
        name            = resolve_variables(variables, name)
        databases[name] = _read_database(element, variables)
    return databases

def _collect_task_children(element, dirname):
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
            args = dict((c.tag, c.text.strip()) for c in child)
            children.append((child.tag, name, args))
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

def _read_tasks(cfgtree, dirname):
    tasks = {}
    for element in cfgtree.iterfind('task'):
        name        = element.get('name').strip()
        actions     = _collect_task_children(element, dirname)
        tasks[name] = Task(name, actions, tasks)
    return tasks

def _read_service(name, filename):
    cfgtree = etree.parse(filename)
    dirname = os.path.dirname(filename)
    tasks   = _read_tasks(cfgtree, dirname)
    element = cfgtree.find('service')
    actions = _collect_task_children(element, dirname)
    service = Service(name, actions, tasks)
    print 'Service "%s" initialized.' % name
    return service

def _read_inotify_daemon(element, variables, queues, databases):
    name       = element.get('name').strip()
    name       = resolve_variables(variables, name)
    directory  = element.find('directory').text.strip()
    directory  = resolve_variables(variables, directory)
    queue_name = element.find('queue').text.strip()
    queue_name = resolve_variables(variables, queue_name)
    db_name    = element.find('database').text.strip()
    db_name    = resolve_variables(variables, db_name)

    services = {}
    for service in element.iterfind('load-service'):
        name           = service.get('name').strip()
        name           = resolve_variables(variables, name)
        path           = service.get('path').strip()
        path           = resolve_variables(variables, path)
        services[name] = _read_service(name, path)

    return INotifyDaemon(name,
                         directory = directory,
                         database  = databases[db_name],
                         queue     = queues[queue_name],
                         services  = services)

def _read_daemons(cfgtree, variables, accounts, databases):
    daemons = {}
    for element in cfgtree.iterfind('daemon'):
        type = element.get('type').strip()
        type = resolve_variables(variables, type)
        name = element.get('name').strip()
        name = resolve_variables(variables, name)
        if type == 'inotify':
            daemon = _read_inotify_daemon(element,
                                          variables,
                                          accounts,
                                          databases)
        else:
            raise Exception('No such daemon type: %s' % type)
        daemons[name] = daemon
    return daemons

def get_inotify_daemon_dir(filename, server_name):
    cfgtree = etree.parse(filename)
    daemon  = cfgtree.find('daemon[@name="%s"]' % server_name)
    return daemon.find('directory').text.strip()

def get_inotify_daemon_db_name(filename, server_name):
    cfgtree = etree.parse(filename)
    daemon  = cfgtree.find('daemon[@name="%s"]' % server_name)
    return daemon.find('database').text.strip()

def init_database(filename, db_name):
    """
    Reads the config file and inits the databases only.
    """
    cfgtree   = etree.parse(filename)
    variables = _read_variables(cfgtree)
    element   = cfgtree.find('database[@name="%s"]' % db_name)
    return _read_database(element, variables)

def init(filename):
    """
    Reads the config file and inits all objects that are defined
    by it.
    """
    cfgtree = etree.parse(filename)
    class Config:
        variables = _read_variables(cfgtree)
        accounts  = _read_account_pools(cfgtree, variables)
        databases = _read_databases(cfgtree, variables)
        queues    = _read_queues(cfgtree, variables, accounts)
        daemons   = _read_daemons(cfgtree, variables, queues, databases)
    return Config()
