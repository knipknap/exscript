import re, time, random

def resolve_variables(variables, string):
    def variable_sub_cb(match):
        field   = match.group(0)
        escape  = match.group(1)
        varname = match.group(2)
        value   = variables.get(varname)

        # Check the variable name syntax.
        if escape:
            return '$' + varname
        elif varname == '':
            return '$'

        # Check the variable value.
        if value is None:
            msg = 'Undefined variable %s' % repr(varname)
            raise Exception(msg)
        return str(value)

    string_re = re.compile(r'(\\?)\$([\w_]*)')
    return string_re.sub(variable_sub_cb, string)

def mkorderid(prefix):
    rand = random.randint(0, 99999)
    return prefix + '_' + str(time.time()) + '-' + str(rand)
