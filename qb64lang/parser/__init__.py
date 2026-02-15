from .ast import SymbolStore
from .context import ParseContext
from .diagnostics import DiagnosticStore
from .parsers import do_main
from .typerules import typecheck

"""
Below are definitions for almost all built-in commands. Omitted are infix operators,
structural keywords, declarations and those with highly custom syntax.
The following metacommands are used heavily:
 - $overload to allow declaring the same name multiple times, with different
   type signatures.
 - $syntax to specify special syntax rules. This is a comma-separated list of flags:
    - strictsigil: for functions returning string, require the $ always be present. For
      functions returning a number, require no sigil be used.
"""
HEADER = """
$overload:on
$syntax:strictsigil
declare sub mkdir (path$)
declare sub out (address%, value%)
declare function left$ (s$, i&&)
declare function lcase$ (s$)
declare function val## (s$)
declare sub _autodisplay
declare function _autodisplay%%
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
