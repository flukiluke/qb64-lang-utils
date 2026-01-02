import dataclasses
from typing import Any

import qbparse.ast
from qbparse import builtins, parse
from qbparse.diagnostics import DiagTemplate


def builtin_proc(name: str):
    for proc in builtins.PROCS:
        if proc.name == name:
            return proc
    raise ValueError("No such builtin procedure " + name)


def check(
    input: str,
    expected: qbparse.ast.Node | None = None,
    d: DiagTemplate | None = None,
):
    prog = parse("?" + input)
    if d is not None:
        assert prog.diagnostics.has(d)
    else:
        expr = prog.main.find(qbparse.ast.Expr)
        assert expr == expected
        assert len(prog.diagnostics.diagnostics) == 0


class Ast(qbparse.ast.Statement, qbparse.ast.LValue):
    def __init__(self, kind: type[qbparse.ast.Node], *args: Any, **kwargs: Any):
        self.kind = kind
        self.props: dict[str, Any] = {}
        pos_fields = list(
            filter(lambda f: not f.kw_only, dataclasses.fields(self.kind))
        )
        if len(args) > len(pos_fields):
            raise ValueError("Too many positional arguments")
        for field, value in zip(pos_fields, args):
            self.props[field.name] = value
        field_names = {field.name for field in dataclasses.fields(self.kind)}
        for name, value in kwargs.items():
            if name not in field_names:
                raise ValueError("Unknown property " + name)
            if name in self.props:
                raise ValueError(f"Property {name} is both positional and keyword")
            self.props[name] = value

    def __repr__(self):
        return (
            self.kind.__name__
            + "("
            + ", ".join([f"{name}={value}" for name, value in self.props.items()])
            + ")"
        )

    def __eq__(self, other: object):
        if not isinstance(other, self.kind):
            return False
        return _test_props(other, self.props)


def _test_props(other: object, props: dict[str, Any]):
    for prop, value in props.items():
        try:
            if getattr(other, prop) != value:
                print(f"Mismatch on {prop}:\n{getattr(other, prop)}\n\n{value}")
                return False
        except AttributeError:
            return False
    return True
