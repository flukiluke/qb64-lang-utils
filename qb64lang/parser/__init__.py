from .ast import SymbolStore
from .context import ParseContext
from .diagnostics import DiagnosticStore
from .parsers import do_main
from .typerules import typecheck


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
