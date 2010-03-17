#!/usr/bin/env python
import os, base64
from lxml          import etree
from Exscript      import Account, Queue
from INotifyDaemon import INotifyDaemon
from Service       import Service
from Task          import Task
from util          import resolve_variables

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

def _collect_task_children(element, dirname):
    children = []
    for child in element:
        if child.tag in ('sendline', 'execline', 'set-prompt'):
            children.append((child.tag, child.text))
        elif child.tag == 'invoke-task':
            name = child.get('name').strip()
            args = dict((c.tag, c.text.strip()) for c in child)
            children.append((child.tag, name, args))
        elif child.tag == 'invoke-script':
            language = child.get('language').strip()
            filename = os.path.join(dirname, child.text.strip())
            if not os.path.isfile(filename):
                raise Exception('not a valid file: ' + filename)
            children.append((child.tag, language, filename))
        else:
            raise Exception('Invalid tag %s' % child.tag)
    return children

def _read_tasks(cfgtree, dirname):
    tasks = {}
    for element in cfgtree.iterfind('task'):
        name        = element.get('name').strip()
        actions     = _collect_task_children(element, dirname)
        tasks[name] = Task(actions, tasks)
    return tasks

def _read_service(filename):
    print "Reading service from", filename
    cfgtree = etree.parse(filename)
    dirname = os.path.dirname(filename)
    tasks   = _read_tasks(cfgtree, dirname)
    element = cfgtree.find('service')
    actions = _collect_task_children(element, dirname)
    return Service(actions, tasks)

def _read_inotify_daemon(element, variables, queues):
    name       = element.get('name').strip()
    name       = resolve_variables(variables, name)
    input_dir  = element.find('in').text.strip()
    input_dir  = resolve_variables(variables, input_dir)
    output_dir = element.find('out').text.strip()
    output_dir = resolve_variables(variables, output_dir)
    queue_name = element.find('queue').text.strip()
    queue_name = resolve_variables(variables, queue_name)

    services = {}
    for service in element.iterfind('load-service'):
        name           = service.get('name').strip()
        name           = resolve_variables(variables, name)
        path           = service.get('path').strip()
        path           = resolve_variables(variables, path)
        services[name] = _read_service(path)

    return INotifyDaemon(name,
                         input_dir  = input_dir,
                         output_dir = output_dir,
                         queue      = queues[queue_name],
                         services   = services)

def _read_daemons(cfgtree, variables, accounts):
    daemons = {}
    for element in cfgtree.iterfind('daemon'):
        type = element.get('type').strip()
        type = resolve_variables(variables, type)
        name = element.get('name').strip()
        name = resolve_variables(variables, name)
        if type == 'inotify':
            daemon = _read_inotify_daemon(element,
                                          variables,
                                          accounts)
        else:
            raise Exception('No such daemon type: %s' % type)
        daemons[name] = daemon
    return daemons

def init(filename):
    """
    Reads the config file and inits all objects that are defined
    by it.
    """
    cfgtree = etree.parse(filename)
    class Config:
        variables = _read_variables(cfgtree)
        accounts  = _read_account_pools(cfgtree, variables)
        queues    = _read_queues(cfgtree, variables, accounts)
        daemons   = _read_daemons(cfgtree, variables, queues)
    return Config()
