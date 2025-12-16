from qbparse.ast import UserProcDefinition
from qbparse.context import ParseContext
from qbparse.datatypes import TYPE__NONE, TypeSignature
from qbparse.parsers import do_block
from qbparse.store import SymbolStore
from qbparse.symbols import Procedure
from qbparse.typerules import typecheck


class Program:
    def __init__(self):
        self.errors = list[str]()
        self.globals = SymbolStore()
        self.main = UserProcDefinition("_main", TypeSignature(TYPE__NONE, []))
        self.globals.add_procedure(Procedure("_main", [self.main]))

    def add_parse(self, input: str):
        ctx = ParseContext(input, self.globals)
        self.main.statements.extend(do_block(ctx))


def parse(input: str):
    program = Program()
    program.add_parse(input)
    typecheck(program)
    return program
