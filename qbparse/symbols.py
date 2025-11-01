from typing import TYPE_CHECKING, Any

from qbparse.datatypes import (
    BUILTIN_SIGILS,
    BUILTIN_TYPES,
    FixedWidthType,
    Type,
    TypeSignature,
)
from qbparse.errors import ParseError

if TYPE_CHECKING:
    from qbparse.ast import ProcDefinition

KEYWORDS = set(
    [
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
        "loop",
        "wend",
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


class Variable:
    def __init__(self, name: str, type: Type):
        self.name = name
        self.type = type

    def __repr__(self):
        return f"[Variable name={self.name} type={self.type}]"

    def __eq__(self, other: Any):
        if type(self) is not type(other):
            return NotImplemented
        return self.name == other.name and self.type == other.type


class Procedure:
    def __init__(self, name: str, signature: TypeSignature | None):
        self.name = name
        # signature & impl may be None for special cased procedures
        self.signature = signature
        self.impl: ProcDefinition | None = None

    def __repr__(self):
        return (
            f"[Procedure name={self.name} signature={self.signature} impl={self.impl}]"
        )

    def __eq__(self, other: Any):
        if type(self) is not type(other):
            return NotImplemented
        return self.name == other.name and self.signature == other.signature


BUILTIN_PROCS: dict[str, Procedure] = {}


class SymbolStore:
    def __init__(self):
        self.variables: dict[str, dict[Type, Variable]] = {}
        self.procedures: dict[str, Procedure] = {}
        self.types: dict[str, Type] = {}
        self.default_type = BUILTIN_TYPES["single"]

    def __repr__(self):
        return (
            f"[SymbolStore variables={self.variables} procedures={self.procedures}"
            f"types={self.types}]"
        )

    def is_keyword(self, name: str):
        return name in KEYWORDS

    def find_procedure(self, ident: str):
        return self.procedures.get(ident) or BUILTIN_PROCS.get(ident)

    def find_variable(self, ident: str, sigil: str | None = None):
        if ident not in self.variables:
            return None
        vars = self.variables[ident]
        typ = self.lookup_sigil(sigil)
        return vars.get(typ)

    def lookup_sigil(self, sigil: str | None):
        if sigil is None:
            return self.default_type
        if builtin := BUILTIN_SIGILS.get(sigil):
            return builtin
        for s in ["`", "~`", "$"]:
            if sigil.startswith(s):
                base_type = BUILTIN_SIGILS[s]
                width = int(sigil.strip("`~$"))
                break
        else:
            raise ParseError("Unknown type " + sigil)
        full_name = base_type.name + " * " + str(width)
        return self.types.setdefault(full_name, FixedWidthType(base_type, width))

    def create_local(self, name: str, type: Type | None):
        if type is None:
            type = self.default_type
        typeset = self.variables.setdefault(name, {})
        if type in typeset:
            raise ParseError("Duplicate variable")
        typeset[type] = Variable(name, type)
        return typeset[type]
