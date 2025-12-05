from qbparse import builtins


def builtin_proc(name: str):
    for proc in builtins.PROCS:
        if proc.name == name:
            return proc
    raise ValueError("No such builtin procedure " + name)
