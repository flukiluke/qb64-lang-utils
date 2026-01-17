from qbparse.ast import SymbolStore
from qbparse.context import ParseContext
from qbparse.diagnostics import DiagnosticStore
from qbparse.parsers import do_main
from qbparse.typerules import typecheck


class Program:
    def __init__(self, input: str):
        self.input = input
        self.diagnostics = DiagnosticStore()
        self.symbols = SymbolStore()
        ctx = ParseContext(input, self.symbols, self.diagnostics)
        self.main = do_main(ctx)


def parse(input: str):
    program = Program(input)
    typecheck(program)
    return program
