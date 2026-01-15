import qbparse.builtins as builtins
from qbparse.datatypes import BUILTIN_SIGILS, TYPE_SINGLE, BitnType, StringType, Type
from qbparse.diagnostics import ParseError
from qbparse.symbols import Procedure, Variable


class SymbolStore:
    def __init__(self):
        self.variables: dict[str, dict[str, Variable]] = {}
        self.procedures: dict[str, Procedure] = {}
        self.types: dict[str, Type] = {}
        self.default_type: Type = TYPE_SINGLE
        for proc in builtins.PROCS:
            self.add_procedure(proc)

    def __repr__(self):
        return (
            f"[SymbolStore variables={self.variables} procedures={self.procedures}"
            f"types={self.types}]"
        )

    def is_keyword(self, name: str):
        return name in builtins.KEYWORDS

    def find_procedure(self, ident: str) -> Procedure | None:
        return self.procedures.get(ident)

    def find_variable(self, ident: str, sigil: str | None = None) -> Variable | None:
        if ident not in self.variables:
            return None
        vars = self.variables[ident]
        type = self.lookup_sigil(sigil)
        return vars.get(type.name)

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
        typeset = self.variables.setdefault(name, {})
        if type.name in typeset:
            raise ParseError("Duplicate variable")
        typeset[type.name] = Variable(name, type)
        return typeset[type.name]

    def add_procedure(self, procedure: Procedure):
        if procedure.name in self.procedures:
            raise ParseError(f"Duplicate procedure definition of {procedure.name}")
        self.procedures[procedure.name] = procedure

    def is_proc_name_free(self, name: str):
        return name not in self.procedures and name not in self.variables
