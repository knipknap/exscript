from __future__ import print_function
# This script is not meant to provide a fully automated test, it's
# merely a hack/starting point for investigating memory consumption
# manually. The behavior also depends heavily on the version of meliae.
import gc
import re
from Exscript.protocols import connect
from Exscript.util.decorator import bind
from Exscript import Queue, Account, Host

objnames = ('count_calls',)
follow_modules = False

def count_calls(conn, thedata, **kwargs):
    thedata['n_calls'] += 1

def foobar():
    pass

queue = Queue()
data  = {'n_calls': 0}
func  = bind(count_calls, data)
task  = queue.run(['t1', 't2', 't3', 't4', 't5', 't6'], func)
task.wait()
queue.shutdown()
queue.destroy()

del func

# Test memory consumption.
from meliae import scanner
gc.collect()
scanner.dump_all_objects("test.dump")
from meliae import loader
om = loader.load('test.dump')
om.remove_expensive_references()
om.collapse_instance_dicts()
om.compute_referrers()
om.compute_total_size()
#print om.summarize()

from pprint import pprint as pp

def larger(x, y):
    return om[y].total_size - om[x].total_size

def larger(x, y):
    return int(y.total_size - x.total_size)

objs = sorted(om.objs.itervalues(), larger)

def is_builtin(o):
    return o.type_str in ('builtin_function_or_method',)

def contains_builtin(reflist):
    for ref in reflist:
        if is_builtin(om[ref]):
            return True
    return False

def is_basic_type(o):
    return o.type_str in ('int', 'str', 'bool', 'NoneType')

def print_obj(lbl, o, indent = 0):
    print((" " * indent) + lbl, o.address, o.type_str, o.name, o.total_size, o.referrers)

def print_ref(o, indent = 0, done = None):
    if o.type_str == '<ex-reference>':
        return
    if not is_basic_type(o):
        print_obj('Ref:', o, indent)
        #for ref in o.referrers:
        #    print_obj_recursive(om[ref], indent + 1, done)

def print_obj_recursive(o, indent = 0, done = None):
    if o.type_str == 'frame':
        print_obj('Frame:', o, indent)
        return
    if o.type_str == 'module' and not follow_modules:
        print_obj('Module:', o, indent)
        return

    if done is None:
        done = set()
    elif o.address in done:
        print_obj('Did that:', o, indent)
        return
    done.add(o.address)

    builtin = contains_builtin(o.ref_list)
    if builtin:
        print_obj('Builtin:', o, indent)
    else:
        print_obj('Obj:', o, indent)

    for ref in o.referrers:
        child = om[ref]
        print_obj_recursive(child, indent + 1, done)

    if not builtin:
        for ref in o.ref_list:
            print_ref(om[ref], indent + 1, done)

for obj in objs:
    if obj.type_str in objnames:
        print_obj_recursive(obj)
    if obj.name and obj.name in objnames:
        print_obj_recursive(obj)

#for addr in sorted(set(thedict.ref_list), larger):
#    print om[addr]
