from typing import TYPE_CHECKING, Any

from qbparse.datatypes import (
    BUILTIN_SIGILS,
    TYPE_SINGLE,
    BitnType,
    StringType,
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
        self.variables: dict[str, dict[str, Variable]] = {}
        self.procedures: dict[str, Procedure] = {}
        self.types: dict[str, Type] = {}
        self.default_type = TYPE_SINGLE

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
        type = self.lookup_sigil(sigil)
        return vars.get(type.name)

    def lookup_sigil(self, sigil: str | None):
        if sigil is None:
            return self.default_type
        if builtin := BUILTIN_SIGILS.get(sigil):
            return builtin
        if sigil.startswith("`"):
            new_type = BitnType.of_signed(int(sigil[1:]))
        elif sigil.startswith("~`"):
            new_type = BitnType.of_unsigned(int(sigil[2:]))
        elif sigil.startswith("$"):
            max_len = int(sigil[1:])
            if max_len == 0:
                raise ParseError("String maximum width cannot be 0")
            new_type = StringType.of_max_len(max_len)
        else:
            raise ParseError("Unknown type " + sigil)
        return self.types.setdefault(new_type.name, new_type)

    def create_local(self, name: str, type: Type | None):
        if type is None:
            type = self.default_type
        typeset = self.variables.setdefault(name, {})
        if type.name in typeset:
            raise ParseError("Duplicate variable")
        typeset[type.name] = Variable(name, type)
        return typeset[type.name]
