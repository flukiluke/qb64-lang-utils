from ast_nodes import Procedure
from datatypes import FixedWidthType, Type, Variable
from errors import ParseError

BUILTIN_TYPES = {
    "_none": Type("_none"),
    "_bit": Type("_bit"),
    "_byte": Type("_byte"),
    "integer": Type("integer"),
    "long": Type("long"),
    "_integer64": Type("_integer64"),
    "_offset": Type("_offset"),
    "_unsigned _bit": Type("_unsigned _bit"),
    "_unsigned _byte": Type("_unsigned _byte"),
    "_unsigned integer": Type("_unsigned integer"),
    "_unsigned long": Type("_unsigned long"),
    "_unsigned _integer64": Type("_unsigned _integer64"),
    "_unsigned _offset": Type("_unsigned _offset"),
    "single": Type("single"),
    "double": Type("double"),
    "_float": Type("_float"),
    "string": Type("string"),
}

BUILTIN_SIGILS = {
    "`": BUILTIN_TYPES["_bit"],
    "%%": BUILTIN_TYPES["_byte"],
    "%": BUILTIN_TYPES["integer"],
    "&": BUILTIN_TYPES["long"],
    "&&": BUILTIN_TYPES["_integer64"],
    "%&": BUILTIN_TYPES["_offset"],
    "~`": BUILTIN_TYPES["_unsigned _bit"],
    "~%%": BUILTIN_TYPES["_unsigned _byte"],
    "~%": BUILTIN_TYPES["_unsigned integer"],
    "~&": BUILTIN_TYPES["_unsigned long"],
    "~&&": BUILTIN_TYPES["_unsigned _integer64"],
    "~%&": BUILTIN_TYPES["_unsigned _offset"],
    "!": BUILTIN_TYPES["single"],
    "#": BUILTIN_TYPES["double"],
    "##": BUILTIN_TYPES["_float"],
    "$": BUILTIN_TYPES["string"],
}

BUILTIN_PROCS: dict[str, Procedure] = {}

KEYWORDS = set(
    [
        "as",
        "const",
        "goto",
        "exit",
        "if",
        "then",
        "else",
        "elseif",
        "endif",
        "end",
        "do",
        "while",
        "loopwend",
        "print",
        "?",
    ]
)


class SymbolStore:
    def __init__(self):
        self.variables: dict[str, dict[Type, Variable]] = {}
        self.procedures: dict[str, Procedure] = {}
        self.types: dict[str, Type] = {}
        self.default_type = BUILTIN_TYPES["single"]

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
