from .ast import SymbolStore
from .context import ParseContext
from .diagnostics import DiagnosticStore
from .parsers import do_main, do_prepass
from .typerules import typecheck

"""
Below are declarations for almost all built-in commands. Omitted are infix operators,
structural keywords, declarations and those with highly custom syntax.
The following metacommands are used:
 - $builtin to generally flag these as built-ins
 - $overload to allow declaring the same name multiple times, with different
   type signatures.
 - $syntax to specify special syntax rules. This is a comma-separated list of flags:
    - strictsigil: for functions returning string, require the $ always be present. For
      functions returning a number, require no sigil be used.
"""
HEADER = """
$builtin:on
$overload:on
$syntax:strictsigil
declare sub MkDir (path$)
declare sub Out (address%, value%)
declare function Left$ (s$, i&&)
declare function LCase$ (s$)
declare function Val## (s$)
declare sub _AutoDisplay
declare function _AutoDisplay%%
"""


class Program:
    def __init__(self, input: str):
        self.input = input
        self.diagnostics = DiagnosticStore()
        self.symbols = SymbolStore()
        do_prepass(ParseContext(HEADER, self.symbols, self.diagnostics))
        do_prepass(ParseContext(input, self.symbols, self.diagnostics))
        self.main = do_main(ParseContext(input, self.symbols, self.diagnostics))


def parse(input: str):
    program = Program(input)
    typecheck(program)
    program.diagnostics.sort()
    return program
