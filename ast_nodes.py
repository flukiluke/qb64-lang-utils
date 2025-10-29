from __future__ import annotations

from collections.abc import Generator, Iterable
from typing import Any

from datatypes import BUILTIN_TYPES, Type, TypeSignature


class Node:
    def children(self) -> Iterable[Node]:
        return ()

    def find(self, kind: type[Node], **props: Any) -> Node | None:
        return next(self.find_all(kind, **props), None)

    def find_all(self, kind: type[Node], **props: Any) -> Generator[Node]:
        if isinstance(self, kind) and self._test_props(props):
            yield self
        for node in self.children():
            yield from node.find_all(kind, **props)

    def _test_props(self, props: Any):
        for prop, value in props.items():
            try:
                if getattr(self, prop) != value:
                    return False
            except AttributeError:
                return False
        return True


class Statement(Node):
    pass


class Procedure(Node):
    def __init__(self, name: str, signature: TypeSignature | None):
        self.name = name
        # signature may be None for special cased procedures
        self.signature = signature
        self.statements: list[Statement] = []

    def __repr__(self):
        return (
            f"[Procedure name={self.name} signature={self.signature}"
            f"statements={self.statements}]"
        )

    def __eq__(self, other: Any):
        if type(self) is not type(other):
            return NotImplemented
        return (
            self.name == other.name
            and self.signature == other.signature
            and self.statements == other.statements
        )

    def children(self):
        return self.statements


class Expr(Node):
    pass


class BinOp(Expr):
    def __init__(self, name: str, left: Expr, right: Expr):
        self.name = name
        self.left = left
        self.right = right

    def __repr__(self):
        return f"[BinOp name={self.name} left={self.left} right={self.right}]"

    def __eq__(self, other: Any):
        if type(self) is not type(other):
            return NotImplemented
        return (
            self.name == other.name
            and self.left == other.left
            and self.right == other.right
        )

    def children(self):
        return (self.left, self.right)


class UniOp(Expr):
    def __init__(self, name: str, param: Expr):
        self.name = name
        self.param = param

    def __repr__(self):
        return f"[UniOp name={self.name} param={self.param}]"

    def __eq__(self, other: Any):
        if type(self) is not type(other):
            return NotImplemented
        return self.name == other.name and self.param == other.param

    def children(self):
        return (self.param,)


class Call(Expr, Statement):
    pass


class Constant(Expr):
    def __init__(self, value: str | int | float, type: Type):
        self.value = value
        self.type = type

    def __repr__(self):
        return f"[Constant value={repr(self.value)} type={self.type}]"

    def __eq__(self, other: Any):
        if type(self) is not type(other):
            return NotImplemented
        return self.value == other.value and self.type == other.type


class Print(Statement):
    TAB_SEPARATOR = Constant("\t", BUILTIN_TYPES["string"])
    FINAL_NEWLINE = Constant("\n", BUILTIN_TYPES["string"])

    def __init__(self):
        self.params: list[Expr] = []

    def __repr__(self):
        return f"[Print params={self.params}]"

    def __eq__(self, other: Any):
        if type(self) is not type(other):
            return NotImplemented
        return self.params == other.params

    def children(self):
        return self.params
