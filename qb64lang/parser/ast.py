from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import chain
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from .datatypes import (
    BUILTIN_SIGILS,
    BUILTIN_TYPES,
    FLOAT_TYPES,
    INTEGRAL_TYPES,
    TYPE__BYTE,
    TYPE__NONE,
    TYPE_ANY,
    TYPE_SINGLE,
    TYPE_STRING,
    BitnType,
    CompoundField,
    CompoundType,
    ExtendedFloat,
    Parameter,
    StringType,
    Type,
    TypeSignature,
)
from .diagnostics import ParseError

if TYPE_CHECKING:
    from . import Program


@dataclass
class LocalScope:
    variables: dict[str, dict[str, "Variable"]] = field(default_factory=dict)


@dataclass
class Node:
    _T = TypeVar("_T", bound="Node")

    lex_start: int = field(kw_only=True, repr=False)
    lex_end: int = field(kw_only=True, repr=False)

    def get_source_repr(self, source: str):
        if self.lex_start == -1 or self.lex_end == -1:
            assert False, "Cannot get source repr of internal node"
        return source[self.lex_start : self.lex_end]

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
class ProcDefinition(Node):
    name: str
    signature: TypeSignature
    symbols: LocalScope = field(default_factory=LocalScope, repr=False)
    statements: list[Statement] = field(default_factory=list, repr=False)
    decl_only: bool = False
    strictsigil: bool = False

    def children(self):
        return self.statements


@dataclass
class ProcDefinitionLocation(Statement):
    proc: ProcDefinition

    def children(self):
        return [self.proc]


@dataclass
class ProcDeclaration(Statement):
    name: str
    signature: TypeSignature


@dataclass
class CompoundDefinition(Statement):
    type: CompoundType


@dataclass
class Dim(Statement):
    variables: list["Variable"]
    is_redim: bool
    # Initial AS T clause if present
    leading_type: Type | None


@dataclass
class Expr(Node):
    expr_type: Type = field(default_factory=lambda: TYPE__NONE, kw_only=True)
    parens: int = field(default=0, kw_only=True)


class LValue(Expr):
    pass


@dataclass
class Var(LValue):
    target: "Variable"


@dataclass
class FieldAccess(LValue):
    base: LValue
    field: CompoundField

    def children(self):
        return [self.base]


@dataclass
class Call(Expr, Statement):
    class Style(Enum):
        FUNCTION = auto()
        INFIX = auto()
        PREFIX = auto()
        STATEMENT = auto()

    target: "Procedure"
    args: list[Expr] = field(default_factory=list)
    style: Style = Style.FUNCTION
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

    @staticmethod
    def wrap(expr: Expr, type: Type):
        return Cast(expr, type, lex_start=expr.lex_start, lex_end=expr.lex_end)


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
    class Element(Enum):
        COMMA = auto()
        SEMICOLON = auto()
        USING = auto()

    args: list[Expr | Element] = field(default_factory=list)

    def children(self):
        return cast(Iterable[Expr], filter(lambda c: isinstance(c, Expr), self.args))


@dataclass
class If(Statement):
    guard: Expr
    true_branch: list[Statement] = field(default_factory=list, repr=False)
    elseifs: list[tuple[Expr, list[Statement]]] = field(
        default_factory=list, repr=False
    )
    false_branch: list[Statement] = field(default_factory=list, repr=False)
    # For the convenience of the formatter
    is_single_line: bool = False

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
    top_guard: Expr | None
    block: list[Statement]
    bottom_guard: Expr | None

    def children(self):
        return chain(
            [self.top_guard] if self.top_guard else [],
            self.block,
            [self.bottom_guard] if self.bottom_guard else [],
        )


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
    impl: ProcDefinition
    value: Expr

    def children(self):
        return [self.value]


@dataclass
class Procedure:
    name: str
    source_name: str
    impls: list[ProcDefinition] = field(default_factory=list, repr=False)
    builtin: bool = True

    def sigs(self):
        return [i.signature for i in self.impls]

    def find_impl(self, sig: TypeSignature):
        for probe_impl in self.impls:
            if sig.equivalent_to(probe_impl.signature):
                return probe_impl
        return None


@dataclass
class Variable:
    name: str
    source_name: str
    type: Type


def _generic(
    name: str,
    ret: Type | None,
    params: list[Parameter | None],
    concretes: Iterable[Type],
) -> list[ProcDefinition]:
    results = list[ProcDefinition]()
    for concrete in concretes:
        results.append(
            ProcDefinition(
                name,
                TypeSignature(
                    ret if ret else concrete,
                    [p if p else Parameter(concrete) for p in params],
                ),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            )
        )
    return results


KEYWORDS = {
    # Misc
    "to": "To",
    # Declarations
    "dim": "Dim",
    "redim": "ReDim",
    "as": "As",
    "_unsigned": "_Unsigned",
    "const": "Const",
    "sub": "Sub",
    "function": "Function",
    "declare": "Declare",
    "type": "Type",
    # Conditionals
    "if": "If",
    "then": "Then",
    "else": "Else",
    "elseif": "ElseIf",
    "endif": "End If",
    "end": "End",
    # Loops
    "do": "Do",
    "while": "While",
    "until": "Until",
    "loop": "Loop",
    "wend": "Wend",
    "for": "For",
    "next": "Next",
    "step": "Step",
    # Flow control
    "goto": "Goto",
    "exit": "_Exit",
    # Operators
    "imp": "Imp",
    "eqv": "Eqv",
    "xor": "Xor",
    "or": "Or",
    "and": "And",
    "not": "Not",
    "mod": "Mod",
    # I/O
    "print": "Print",
    "?": "Print",
    "using": "Using",
}

PROCS = [
    # Comparison operators
    Procedure(
        "=",
        "=",
        [
            ProcDefinition(
                "=",
                TypeSignature(TYPE__BYTE, [Parameter(TYPE_ANY), Parameter(TYPE_ANY)]),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            )
        ],
    ),
    Procedure(
        "<>",
        "<>",
        [
            ProcDefinition(
                "<>",
                TypeSignature(TYPE__BYTE, [Parameter(TYPE_ANY), Parameter(TYPE_ANY)]),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            )
        ],
    ),
    Procedure(
        "<",
        "<",
        [
            ProcDefinition(
                "<",
                TypeSignature(
                    TYPE__BYTE, [Parameter(TYPE_STRING), Parameter(TYPE_STRING)]
                ),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            ),
            *_generic("<", TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic("<", TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure(
        ">",
        ">",
        [
            ProcDefinition(
                ">",
                TypeSignature(
                    TYPE__BYTE, [Parameter(TYPE_STRING), Parameter(TYPE_STRING)]
                ),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            ),
            *_generic(">", TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(">", TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure(
        "<=",
        "<=",
        [
            ProcDefinition(
                "<=",
                TypeSignature(
                    TYPE__BYTE, [Parameter(TYPE_STRING), Parameter(TYPE_STRING)]
                ),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            ),
            *_generic("<=", TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic("<=", TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure(
        ">=",
        ">=",
        [
            ProcDefinition(
                ">=",
                TypeSignature(
                    TYPE__BYTE, [Parameter(TYPE_STRING), Parameter(TYPE_STRING)]
                ),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            ),
            *_generic(">=", TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(">=", TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    # Arithmetic
    Procedure(
        "+",
        "+",
        [
            ProcDefinition(
                "+",
                TypeSignature(
                    TYPE_STRING, [Parameter(TYPE_STRING), Parameter(TYPE_STRING)]
                ),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            ),
            # Unary + does nothing, but it's useful to record it for formatting
            *_generic("+", None, [None], INTEGRAL_TYPES),
            *_generic("+", None, [None], FLOAT_TYPES),
            *_generic("+", None, [None, None], INTEGRAL_TYPES),
            *_generic("+", None, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure(
        "-",
        "-",
        [
            *_generic("-", None, [None], INTEGRAL_TYPES),
            *_generic("-", None, [None], FLOAT_TYPES),
            *_generic("-", None, [None, None], INTEGRAL_TYPES),
            *_generic("-", None, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure(
        "*",
        "*",
        [
            *_generic("*", None, [None, None], INTEGRAL_TYPES),
            *_generic("*", None, [None, None], FLOAT_TYPES),
        ],
    ),
    Procedure("/", "/", [*_generic("/", None, [None, None], FLOAT_TYPES)]),
    Procedure("\\", "\\", [*_generic("\\", None, [None, None], INTEGRAL_TYPES)]),
    Procedure("^", "^", [*_generic("^", None, [None, None], FLOAT_TYPES)]),
    Procedure("mod", "Mod", [*_generic("mod", None, [None, None], INTEGRAL_TYPES)]),
    # Bitwise relations
    Procedure("imp", "Imp", [*_generic("imp", None, [None, None], INTEGRAL_TYPES)]),
    Procedure("eqv", "Eqv", [*_generic("eqv", None, [None, None], INTEGRAL_TYPES)]),
    Procedure("xor", "Xor", [*_generic("xor", None, [None, None], INTEGRAL_TYPES)]),
    Procedure("or", "Or", [*_generic("or", None, [None, None], INTEGRAL_TYPES)]),
    Procedure("and", "And", [*_generic("and", None, [None, None], INTEGRAL_TYPES)]),
    Procedure("not", "Not", [*_generic("not", None, [None], INTEGRAL_TYPES)]),
    # Other maths
    Procedure(
        "_atan2", "_Atan2", [*_generic("_atan2", None, [None, None], FLOAT_TYPES)]
    ),
]


class SymbolStore:
    def __init__(self):
        self.global_vars: dict[str, dict[str, Variable]] = {}
        self.scope = LocalScope()
        self.procedures: dict[str, Procedure] = {}
        self.types: dict[str, Type] = {}
        self.default_type: Type = TYPE_SINGLE
        self.return_proc_as_id: bool = False
        self.return_var_as_id: bool = False
        for proc in PROCS:
            self.add_procedure(proc)

    def set_scope(self, scope: LocalScope):
        self.scope = scope

    def is_keyword(self, name: str):
        return name in KEYWORDS

    def find_procedure(self, ident: str) -> Procedure | None:
        return self.procedures.get(ident)

    def find_variable(self, ident: str, type: Type | None) -> Variable | None:
        """
        Lookup variable with name and type in current local scope then global scope.

        If type is None, the requested variable is either of compound type, or the
        default scalar type (priority given to the former). Default scalars in the
        local scope take priority over compound variables in the global scope.
        """

        def find_compound_var(typeset):
            for var in typeset.values():
                if not var.type.is_builtin():
                    return var

        local_typeset = self.scope.variables.get(ident)
        global_typeset = self.global_vars.get(ident)
        if type:
            if local_typeset and (var := local_typeset.get(type.name)):
                return var
            if global_typeset and (var := global_typeset.get(type.name)):
                return var
        else:
            if local_typeset and (var := find_compound_var(local_typeset)):
                return var
            if local_typeset and (var := local_typeset.get(self.default_type.name)):
                return var
            if global_typeset and (var := find_compound_var(global_typeset)):
                return var
            if global_typeset and (var := global_typeset.get(self.default_type.name)):
                return var

    def find_type(self, name: str) -> Type | None:
        return BUILTIN_TYPES.get(name, self.types.get(name))

    def create_compound_type(
        self, name: str, source_name: str, fields: list[CompoundField]
    ):
        new_type = CompoundType(name, source_name, "", fields)
        self.types[name] = new_type
        return new_type

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

    def create_local(self, name: str, cased_name: str, type: Type | None):
        if type is None:
            type = self.default_type
        typeset = self.scope.variables.setdefault(name, {})
        if type.name in typeset:
            raise ParseError("Duplicate variable")
        typeset[type.name] = Variable(name, cased_name, type)
        return typeset[type.name]

    def add_procedure(self, procedure: Procedure):
        if procedure.name in self.procedures:
            raise ParseError(f"Duplicate procedure definition of {procedure.name}")
        self.procedures[procedure.name] = procedure


T = TypeVar("T")


class AstWalk(Generic[T]):
    def __init__(self, program: "Program"):
        self.program = program
        self.handlers: dict[type[Node], Callable] = {
            Assignment: self.assignment,
            Call: self.call,
            Cast: self.cast,
            CompoundDefinition: self.compound_definition,
            Constant: self.constant,
            Dim: self.kw_dim,
            FieldAccess: self.field_access,
            For: self.kw_for,
            If: self.kw_if,
            Loop: self.kw_loop,
            Print: self.kw_print,
            ProcDeclaration: self.proc_declaration,
            ProcDefinition: self.proc_definition,
            ProcDefinitionLocation: self.proc_definition_location,
            SetReturn: self.set_return,
            Var: self.var,
        }

    def evaluate(self, node: Node) -> T:
        return self.handlers[node.__class__](node)

    def assignment(self, node: Assignment) -> T: ...

    def call(self, node: Call) -> T: ...

    def cast(self, node: Cast) -> T: ...

    def compound_definition(self, node: CompoundDefinition) -> T: ...

    def constant(self, node: Constant) -> T: ...

    def kw_dim(self, node: Dim) -> T: ...

    def field_access(self, node: FieldAccess) -> T: ...

    def kw_for(self, node: For) -> T: ...

    def kw_if(self, node: If) -> T: ...

    def kw_loop(self, node: Loop) -> T: ...

    def kw_print(self, node: Print) -> T: ...

    def proc_declaration(self, node: ProcDeclaration) -> T: ...

    def proc_definition(self, node: ProcDefinition) -> T: ...

    def proc_definition_location(self, node: ProcDefinitionLocation) -> T: ...

    def set_return(self, node: SetReturn) -> T: ...

    def var(self, node: Var) -> T: ...
