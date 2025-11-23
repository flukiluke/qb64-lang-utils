from qbparse.ast import ProcDefinition
from qbparse.context import ParseContext
from qbparse.parsers import do_block
from qbparse.symbols import SymbolStore


class Program:
    def __init__(self):
        self.globals = SymbolStore()
        self.main = ProcDefinition()

    def add_parse(self, input: str):
        ctx = ParseContext(input, self.globals)
        self.main.statements.extend(do_block(ctx))


def parse(input: str):
    program = Program()
    program.add_parse(input)
    return program
