from __future__ import annotations

from collections.abc import Generator, Iterable
from dataclasses import dataclass, field
from itertools import chain
from typing import Any

import qbparse.symbols as symbols
from qbparse.datatypes import TYPE_STRING, ExtendedFloat, Type


class Node:
    def children(self) -> Iterable[Node]:
        return ()

    def find(self, kind: type[Node], props: dict[str, Any] = {}) -> Node:
        return next(self.find_all(kind, props))

    def find_all(
        self, kind: type[Node], props: dict[str, Any] = {}, nesting: bool = False
    ) -> Generator[Node]:
        if isinstance(self, kind) and self._test_props(props):
            yield self
            if not nesting:
                return
        for node in self.children():
            yield from node.find_all(kind, props, nesting)

    def _test_props(self, props: dict[str, Any]):
        for prop, value in props.items():
            try:
                if getattr(self, prop) != value:
                    return False
            except AttributeError:
                return False
        return True


class Statement(Node):
    pass


@dataclass
class ProcDefinition(Node):
    statements: list[Statement] = field(default_factory=lambda: [])

    def children(self):
        return self.statements


class Expr(Node):
    pass


class LValue(Expr):
    pass


@dataclass
class Var(LValue):
    target: symbols.Variable


@dataclass
class BinOp(Expr):
    name: str
    left: Expr
    right: Expr

    def children(self):
        return (self.left, self.right)


@dataclass
class UniOp(Expr):
    name: str
    param: Expr

    def children(self):
        return (self.param,)


@dataclass
class Call(Expr, Statement):
    target: symbols.Procedure
    args: list[Expr] = field(default_factory=lambda: [])

    def children(self):
        return self.args


@dataclass
class Cast(Expr):
    expr: Expr
    type: Type

    def children(self):
        return (self.expr,)


@dataclass
class Assignment(Statement):
    lval: LValue
    rval: Expr

    def children(self):
        return (self.lval, self.rval)


@dataclass
class Constant(Expr):
    value: str | int | float | ExtendedFloat
    type: Type


@dataclass
class Print(Statement):
    TAB_SEPARATOR = Constant("\t", TYPE_STRING)
    FINAL_NEWLINE = Constant("\n", TYPE_STRING)

    args: list[Expr] = field(default_factory=lambda: [])

    def children(self):
        return self.args


@dataclass
class If(Statement):
    guard: Expr
    true_branch: list[Statement]
    elseifs: list[tuple[Expr, list[Statement]]]
    false_branch: list[Statement]

    def children(self):
        return chain(
            [self.guard],
            self.true_branch,
            [e[0] for e in self.elseifs],
            *[e[1] for e in self.elseifs],
            self.false_branch,
        )
