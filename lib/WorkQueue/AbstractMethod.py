import sys, exceptions

def _caller(obj):
    fr = sys._getframe(2)
    co = fr.f_code
    return "%s.%s" % (obj.__class__, co.co_name)

def AbstractMethod(obj = None):
    raise Exception(_caller(obj))
