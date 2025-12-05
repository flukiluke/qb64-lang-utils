from qbparse.ast import ProcDefinition
from qbparse.context import ParseContext
from qbparse.datatypes import TYPE__NONE, TypeSignature
from qbparse.parsers import do_block
from qbparse.symbols import Procedure, SymbolStore


class Program:
    def __init__(self):
        self.errors = list[str]()
        self.globals = SymbolStore()
        self.main = ProcDefinition("_main", TypeSignature(TYPE__NONE, []))
        self.globals.add_procedure(Procedure("_main", [self.main]))

    def add_parse(self, input: str):
        ctx = ParseContext(input, self.globals)
        self.main.statements.extend(do_block(ctx))


def parse(input: str):
    program = Program()
    program.add_parse(input)
    return program
