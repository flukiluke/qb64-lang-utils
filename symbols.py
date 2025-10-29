from ast_nodes import Procedure
from datatypes import BUILTIN_SIGILS, BUILTIN_TYPES, FixedWidthType, Type
from errors import ParseError

BUILTIN_PROCS: dict[str, Procedure] = {}

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
    def __init__(self, name: str, typ: Type):
        self.name = name
        self.typ = typ


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

    def find_variable(self, ident: str, sigil: str | None):
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
