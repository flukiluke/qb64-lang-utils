from __future__ import annotations

from collections.abc import Generator, Iterable
from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import chain
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    import qbparse.symbols as symbols

from qbparse.datatypes import (
    TYPE__NONE,
    TYPE_STRING,
    ExtendedFloat,
    Type,
    TypeSignature,
)


@dataclass
class Node:
    _T = TypeVar("_T", bound="Node")

    lex_start: int | None = field(kw_only=True, default=None)
    lex_len: int = field(kw_only=True, default=0)

    def get_lex_range(self) -> tuple[int, int] | None:
        start = self.lex_start
        end = None if start is None else start + self.lex_len
        for child in self.children():
            child_range = child.get_lex_range()
            if child_range is None:
                continue
            child_start, child_end = child_range
            if start is None or child_start < start:
                start = child_start
            if end is None or child_end > end:
                end = child_end
        if start is None or end is None:
            return None
        return (start, end)

    def children(self) -> Iterable[Node]:
        return ()

    def find(self, kind: type[_T], props: dict[str, Any] = {}) -> _T:
        return next(self.find_all(kind, props))

    def find_all(
        self, kind: type[_T], props: dict[str, Any] = {}, nesting: bool = False
    ) -> Generator[_T]:
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
class UserProcDefinition(Node):
    name: str
    signature: TypeSignature
    statements: list[Statement] = field(default_factory=lambda: [])

    def children(self):
        return self.statements


@dataclass
class BuiltinProcDefinition(Node):
    """
    Placeholder class for procedures with no explicit definition because
    they are builtin
    """

    signature: TypeSignature


ProcDefinition = UserProcDefinition | BuiltinProcDefinition


@dataclass
class Expr(Node):
    expr_type: Type = field(default_factory=lambda: TYPE__NONE, kw_only=True)


class LValue(Expr):
    pass


@dataclass
class Var(LValue):
    target: symbols.Variable


@dataclass
class Call(Expr, Statement):
    class Style(Enum):
        STANDARD = auto()
        INFIX = auto()
        PREFIX = auto()

    target: symbols.Procedure
    args: list[Expr] = field(default_factory=lambda: [])
    style: Style = Style.STANDARD
    # Calculated values
    impl: ProcDefinition | None = None

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


@dataclass
class Loop(Statement):
    # Loop while guard is true, UNTIL has a negation added
    guard: Expr
    block: list[Statement]
    # True => DO WHILE/UNTIL or WHILE, False => LOOP WHILE/UNTIL
    top_check: bool

    def children(self):
        return chain([self.guard], self.block)


@dataclass
class For(Statement):
    iterator: Var
    start_value: Expr
    end_value: Expr
    step: Expr
    block: list[Statement]

    def children(self):
        return chain([self.iterator], self.block)
