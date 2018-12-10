import ast

def pre_function_hook():
    import os
    import sys
    from time import perf_counter
    from threading import get_ident
    from multiprocessing import Lock

    _lprof_lock = Lock()
    _lprof_process_id = os.getpid()
    _lprof_thread_id = get_ident()
    _lprof_function_file = sys._getframe(0).f_code.co_filename
    _lprof_function_firstlineno = sys._getframe(0).f_code.co_firstlineno

    if '_lprof_timers' not in sys.modules[__name__].__dict__:
        setattr(sys.modules[__name__], '_lprof_timers', {})

    if '_lprof_stats' not in sys.modules[__name__].__dict__:
        setattr(sys.modules[__name__], '_lprof_stats', {})

    if '_lprof_firstlines' not in sys.modules[__name__].__dict__:
        setattr(sys.modules[__name__], '_lprof_firstlines', set([]))

    sys.modules[__name__]._lprof_firstlines.add(_lprof_function_firstlineno)

    if _lprof_function_file not in sys.modules[__name__]._lprof_stats:
        sys.modules[__name__]._lprof_stats[_lprof_function_file] = {}

    if _lprof_function_file not in sys.modules[__name__]._lprof_timers:
        sys.modules[__name__]._lprof_timers[_lprof_function_file] = {}

    if _lprof_process_id not in sys.modules[__name__]._lprof_timers[_lprof_function_file]:
        sys.modules[__name__]._lprof_timers[_lprof_function_file][_lprof_process_id] = {}

    if _lprof_thread_id not in sys.modules[__name__]._lprof_timers[_lprof_function_file][_lprof_process_id]:
        sys.modules[__name__]._lprof_timers[_lprof_function_file][_lprof_process_id][_lprof_thread_id] = perf_counter()

    def _lprof_tick(lineno, return_val=None):
        current_time = perf_counter()

        try:
            _lprof_lock.acquire()

            if lineno not in sys.modules[__name__]._lprof_stats[_lprof_function_file]:
                sys.modules[__name__]._lprof_stats[_lprof_function_file][lineno] = {'hits': 0, 'time': 0}

            sys.modules[__name__]._lprof_stats[_lprof_function_file][lineno]['hits'] += 1
            sys.modules[__name__]._lprof_stats[_lprof_function_file][lineno]['time'] += perf_counter() - sys.modules[__name__]._lprof_timers[_lprof_function_file][_lprof_process_id][_lprof_thread_id]
            sys.modules[__name__]._lprof_timers[_lprof_function_file][_lprof_process_id][_lprof_thread_id] = perf_counter()
        finally:
            _lprof_lock.release()

        if return_val:
            return return_val


def get_function_node(func):
    with open(func.__code__.co_filename, 'r') as f:
        file_content = f.read()

    tree = ast.parse(file_content)

    for node in ast.walk(tree):
        if (type(node) == ast.FunctionDef and node.lineno == func.__code__.co_firstlineno):
            return node


def profile(func):
    function = get_function_node(func)
    function.decorator_list = []

    first = False
    for node in ast.walk(function):
        
        if (type(node) == ast.Return):
            new_return = ast.parse("return _lprof_tick('%d', return_val=1)" % node.lineno).body[0]
            new_return.value.keywords[0].value = node.value
            node.value = new_return.value

        if 'body' in node.__dict__:
            new_body = []
            lines = set([])

            for entry in node.body:
                if not first:
                    new_body.extend(get_function_node(pre_function_hook).body)
                    first = True

                new_body.append(entry)

                if 'lineno' in entry.__dict__ and entry.lineno not in lines:
                    new_body.extend(ast.parse("_lprof_tick('%d')" % entry.lineno).body)

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
    for fname in _lprof_stats.keys():
        print('-------- Performance overview [ %s ]--------' % (fname))
        print(' Line     Hits     Time                 Code')
        with open(fname, 'r') as f:
            content = f.readlines()

            for firstline in sorted(_lprof_firstlines):
                try:
                    nextfirstline = min(i for i in _lprof_firstlines if i > firstline)
                except:
                    nextfirstline = None

                if nextfirstline:
                    lastline = max([int(i) for i in _lprof_stats[fname].keys() if int(i) < nextfirstline])
                else:
                    lastline = max(map(int, _lprof_stats[fname].keys()))

                for lineno in range(firstline, lastline + 1):
                    lineno = str(lineno)
                    print(format(int(lineno), '5d'), '\t', end='')

                    if lineno in _lprof_stats[fname]:
                        print(format(_lprof_stats[fname][lineno]['hits'], '6d'), '\t', end='')
                        print(format(_lprof_stats[fname][lineno]['time'], '0.8f'), '\t', end='')
                    else:
                        print('     0\t', end='')
                        print('0.00000000\t', end='')
                    print(content[int(lineno)-1].rstrip(), '\t', end='\n')

                print('')

