from collections.abc import Generator, Iterable
from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import chain
from typing import Any, TypeVar

from .datatypes import (
    BUILTIN_SIGILS,
    FLOAT_TYPES,
    INTEGRAL_TYPES,
    TYPE__BYTE,
    TYPE__FLOAT,
    TYPE__INTEGER64,
    TYPE__NONE,
    TYPE_ANY,
    TYPE_INTEGER,
    TYPE_SINGLE,
    TYPE_STRING,
    BitnType,
    ExtendedFloat,
    Parameter,
    StringType,
    Type,
    TypeSignature,
)
from .diagnostics import ParseError


@dataclass
class LocalScope:
    variables: dict[str, dict[str, "Variable"]] = field(default_factory=dict)


@dataclass
class Node:
    _T = TypeVar("_T", bound="Node")

    lex_start: int | None = field(kw_only=True, default=None, repr=False)
    lex_len: int = field(kw_only=True, default=0, repr=False)

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

    def children(self) -> Iterable["Node"]:
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
    symbols: LocalScope = field(default_factory=LocalScope, repr=False)
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
    symbols: LocalScope = field(default_factory=LocalScope, repr=False)


ProcDefinition = UserProcDefinition | BuiltinProcDefinition


@dataclass
class ProcDefinitionLocation(Statement):
    proc: UserProcDefinition


@dataclass
class Expr(Node):
    expr_type: Type = field(default_factory=lambda: TYPE__NONE, kw_only=True)


class LValue(Expr):
    pass


@dataclass
class Var(LValue):
    target: "Variable"


@dataclass
class Call(Expr, Statement):
    class Style(Enum):
        STANDARD = auto()
        INFIX = auto()
        PREFIX = auto()

    target: "Procedure"
    args: list[Expr] = field(default_factory=list)
    style: Style = Style.STANDARD
    # Calculated values
    impl: ProcDefinition | None = None

    def children(self):
        return self.args

    def __repr__(self):
        return (
            f"Call(target={self.target}, args={self.args}, "
            f"impl={self.impl.signature if self.impl else None})"
        )


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


@dataclass
class SetReturn(Statement):
    impl: UserProcDefinition
    value: Expr

    def children(self):
        return [self.value]


@dataclass
class Procedure:
    name: str
    impls: list[ProcDefinition] = field(default_factory=list, repr=False)

    def sigs(self):
        return [i.signature for i in self.impls]


@dataclass
class Variable:
    name: str
    type: Type


def _generic(
    ret: Type | None, params: list[Parameter | None], concretes: Iterable[Type]
) -> list[ProcDefinition]:
    results = list[ProcDefinition]()
    for concrete in concretes:
        results.append(
            BuiltinProcDefinition(
                TypeSignature(
                    ret if ret else concrete,
                    [p if p else Parameter(concrete) for p in params],
                )
            )
        )
    return results


KEYWORDS = set(
    [
        # Misc
        "to",
        # Declarations
        "dim",
        "as",
        "const",
        "sub",
        "function",
        # Conditionals
        "if",
        "then",
        "else",
        "elseif",
        "endif",
        "end",
        # Loops
        "do",
        "while",
        "until",
        "loop",
        "wend",
        "for",
        "next",
        "step",
        # Flow control
        "goto",
        "exit",
        # Operators
        "imp",
        "eqv",
        "xor",
        "or",
        "and",
        "not",
        "mod",
        # I/O
        "print",
        "?",
    ]
)

PROCS = [
    # Comparison operators
    Procedure(
        "=",
        [
            BuiltinProcDefinition(
                TypeSignature(TYPE__BYTE, [Parameter(TYPE_ANY), Parameter(TYPE_ANY)])
            )
        ],
    ),
    Procedure(
        "<>",
        [
            BuiltinProcDefinition(
                TypeSignature(TYPE__BYTE, [Parameter(TYPE_ANY), Parameter(TYPE_ANY)])
            )
        ],
    ),
    Procedure(
        "<",
        [
            BuiltinProcDefinition(
                TypeSignature(
                    TYPE__BYTE, [Parameter(TYPE_STRING), Parameter(TYPE_STRING)]
                )
            ),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure(
        ">",
        [
            BuiltinProcDefinition(
                TypeSignature(
                    TYPE__BYTE, [Parameter(TYPE_STRING), Parameter(TYPE_STRING)]
                )
            ),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure(
        "<=",
        [
            BuiltinProcDefinition(
                TypeSignature(
                    TYPE__BYTE, [Parameter(TYPE_STRING), Parameter(TYPE_STRING)]
                )
            ),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure(
        ">=",
        [
            BuiltinProcDefinition(
                TypeSignature(
                    TYPE__BYTE, [Parameter(TYPE_STRING), Parameter(TYPE_STRING)]
                )
            ),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    # Arithmetic
    Procedure(
        "+",
        [
            BuiltinProcDefinition(
                TypeSignature(
                    TYPE_STRING, [Parameter(TYPE_STRING), Parameter(TYPE_STRING)]
                )
            ),
            *_generic(None, [None, None], INTEGRAL_TYPES),
            *_generic(None, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure(
        "-",
        [
            *_generic(None, [None], INTEGRAL_TYPES),
            *_generic(None, [None], FLOAT_TYPES),
            *_generic(None, [None, None], INTEGRAL_TYPES),
            *_generic(None, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure(
        "*",
        [
            *_generic(None, [None, None], INTEGRAL_TYPES),
            *_generic(None, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure("/", [*_generic(None, [None, None], FLOAT_TYPES)]),
    Procedure("\\", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Procedure("^", [*_generic(None, [None, None], FLOAT_TYPES)]),
    Procedure("mod", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    # Bitwise relations
    Procedure("imp", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Procedure("eqv", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Procedure("xor", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Procedure("or", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Procedure("and", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Procedure("not", [*_generic(None, [None], INTEGRAL_TYPES)]),
    # Other maths
    Procedure("_atan2", [*_generic(None, [None, None], FLOAT_TYPES)]),
    # Everything else
    Procedure(
        "val",
        [BuiltinProcDefinition(TypeSignature(TYPE__FLOAT, [Parameter(TYPE_STRING)]))],
    ),
    Procedure(
        "lcase$",
        [BuiltinProcDefinition(TypeSignature(TYPE_STRING, [Parameter(TYPE_STRING)]))],
    ),
    Procedure(
        "left$",
        [
            BuiltinProcDefinition(
                TypeSignature(
                    TYPE_STRING, [Parameter(TYPE_STRING), Parameter(TYPE__INTEGER64)]
                )
            )
        ],
    ),
    Procedure(
        "mkdir",
        [BuiltinProcDefinition(TypeSignature(TYPE__NONE, [Parameter(TYPE_STRING)]))],
    ),
    Procedure(
        "out",
        [
            BuiltinProcDefinition(
                TypeSignature(
                    TYPE__NONE, [Parameter(TYPE_INTEGER), Parameter(TYPE_INTEGER)]
                )
            )
        ],
    ),
]


class SymbolStore:
    def __init__(self):
        self.global_vars: dict[str, dict[str, Variable]] = {}
        self.scope = LocalScope()
        self.procedures: dict[str, Procedure] = {}
        self.types: dict[str, Type] = {}
        self.default_type: Type = TYPE_SINGLE
        for proc in PROCS:
            self.add_procedure(proc)

    def set_scope(self, scope: LocalScope):
        self.scope = scope

    def is_keyword(self, name: str):
        return name in KEYWORDS

    def find_procedure(self, ident: str) -> Procedure | None:
        return self.procedures.get(ident)

    def find_variable(self, ident: str, sigil: str | None = None) -> Variable | None:
        type_name = self.lookup_sigil(sigil).name
        for pool in self.scope.variables, self.global_vars:
            if (typeset := pool.get(ident)) and (result := typeset.get(type_name)):
                return result
        return None

    def lookup_sigil(self, sigil: str | None) -> Type:
        if sigil is None:
            return self.default_type
        if builtin := BUILTIN_SIGILS.get(sigil):
            return builtin
        if sigil.startswith("`"):
            width = int(sigil[1:])
            new_type = BitnType.of_signed(width)
        elif sigil.startswith("~`"):
            width = int(sigil[2:])
            new_type = BitnType.of_unsigned(width)
        elif sigil.startswith("$"):
            max_len = int(sigil[1:])
            new_type = StringType.of_max_len(max_len)
        else:
            assert False, "Unknown type " + sigil
        return self.types.setdefault(new_type.name, new_type)

    def create_local(self, name: str, type: Type | None):
        if type is None:
            type = self.default_type
        typeset = self.scope.variables.setdefault(name, {})
        if type.name in typeset:
            raise ParseError("Duplicate variable")
        typeset[type.name] = Variable(name, type)
        return typeset[type.name]

    def add_procedure(self, procedure: Procedure):
        if procedure.name in self.procedures:
            raise ParseError(f"Duplicate procedure definition of {procedure.name}")
        self.procedures[procedure.name] = procedure

    def is_proc_name_free(self, name: str):
        for proc in self.procedures.values():
            if name == proc.name:
                return False
            for impl in proc.impls:
                if name in impl.symbols.variables:
                    return False
        return name not in self.global_vars
