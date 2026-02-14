from .ast import SymbolStore
from .context import ParseContext
from .diagnostics import DiagnosticStore
from .parsers import do_main
from .typerules import typecheck

HEADER = """
$overload:on
$syntax:musthave=$
declare function left$ (s$, i&&)
declare sub mkdir (path$)
declare sub out (address%, value%)
$syntax:musthave=$
declare function lcase$ (s$)
declare function val## (s$)
"""


class Program:
    def __init__(self, input: str):
        self.input = input
        self.diagnostics = DiagnosticStore()
        self.symbols = SymbolStore()
        self.main = do_main(ParseContext(HEADER, self.symbols, self.diagnostics))
        # Throw away structural results of parsing the header, we are only interested in
        # the symbols recorded.
        self.main.statements = []
        self.main = do_main(ParseContext(input, self.symbols, self.diagnostics))


def parse(input: str):
    program = Program(input)
    typecheck(program)
    return program
