import ast
import inspect

def __pre_function_hook():
    import time
    import sys
    setattr(sys.modules[__name__], '__tick__', time.perf_counter())
    setattr(sys.modules[__name__], '__line_perf__', {})

def __tick(file_name, line_no):
    if '{0}' not in sys.modules[__name__].__line_perf__:
        sys.modules[__name__].__line_perf__['{0}'] = {{'{2}': 0}}

    if '{1}' not in sys.modules[__name__].__line_perf__['{0}']:
         sys.modules[__name__].__line_perf__['{0}']['{1}'] = 0
    sys.modules[__name__].__line_perf__['{0}']['{1}']+= time.perf_counter() - sys.modules[__name__].__tick__
    setattr(sys.modules[__name__], '__tick__', time.perf_counter())


def get_function_node(func):
    source = inspect.getsource(func)



def profile(func):

    with open(func.__code__.co_filename, 'r') as f:
        file_content = f.read()

    t = ast.parse(file_content)

    function = None
    for node in ast.walk(t):
        if (type(node) == ast.FunctionDef and node.lineno == func.__code__.co_firstlineno):
            function = node

    function.decorator_list = []

    first = False
    for node in ast.walk(function):
        if 'body' in node.__dict__:
            new_body = []
            lines = set([])

            for entry in node.body:
                if not first:
                    new_body.extend(ast.parse(inspect.getsource(__pre_function_hook)).body[0].body)
                    new_body.extend(ast.parse("""import time
import sys
setattr(sys.modules[__name__], '__tick__', time.perf_counter())
setattr(sys.modules[__name__], '__line_perf__', {})
""").body)
                    first = True

                new_body.append(entry)

                if 'lineno' in entry.__dict__ and entry.lineno not in lines:
                    new_body.extend(ast.parse("""
if '{0}' not in sys.modules[__name__].__line_perf__:
    sys.modules[__name__].__line_perf__['{0}'] = {{'{2}': 0}}

if '{1}' not in sys.modules[__name__].__line_perf__['{0}']:
     sys.modules[__name__].__line_perf__['{0}']['{1}'] = 0
sys.modules[__name__].__line_perf__['{0}']['{1}']+= time.perf_counter() - sys.modules[__name__].__tick__
setattr(sys.modules[__name__], '__tick__', time.perf_counter())
""".format(func.__code__.co_filename, entry.lineno, func.__code__.co_firstlineno+1)).body)
                lines.add(entry.lineno)

            node.body = new_body

    module = ast.Module([function])

    def new_func(*args, **kwargs):
        compiled_code = compile(module, func.__code__.co_filename, 'exec')
        namespace = {}
        exec(compiled_code, namespace)
        return namespace[func.__name__](*args, **kwargs)

    return new_func


def dump_perf_stats():
    for fname in __line_perf__:
        print('-------- Performance overview [ %s ]--------' % (fname))
        with open(fname, 'r') as f:
            content = f.readlines()

            for lineno in sorted(__line_perf__[fname].keys()):
                print(format(int(lineno), '4d'), '  ', format(__line_perf__[fname][lineno], 'f'), '\t', content[int(lineno)-1].rstrip())


class Testme():
    def __init__(self):
        pass

    @profile
    def hello(self, howmany):
        import time
        from threading import Thread

        for i in range(howmany):
            time.sleep(0.2)
            print(i)

        def runner():
            for i in range(howmany):
                time.sleep(0.2)
                print(i)

        t = Thread(target=runner)
        t2 = Thread(target=runner)
        t.start()
        #t2.start()
        t.join()
        #t2.join()

Testme().hello(10)

dump_perf_stats()
