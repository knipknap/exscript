def execute(scope, source):
    return dict(map(lambda a: (a,1), source)).keys()
