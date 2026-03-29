from .ast import SymbolStore
from .context import ParseContext
from .diagnostics import DiagnosticStore
from .parsers import do_main, do_prepass
from .typerules import typecheck

"""
Below are declarations for almost all built-in commands. Omitted are infix operators,
structural keywords, declarations and those with highly custom syntax.
The following $flags are used:
 - builtin to generally flag these as built-ins
 - overload to allow declaring the same name multiple times, with different
   type signatures.
 - strictsigil: for functions returning string, require the $ always be present. For
      functions returning a number, require no sigil be used.
"""
HEADER = """
$flags:builtin=on,overload=on,strictsigil=on
declare sub      _AutoDisplay
declare function _AutoDisplay%%
declare function Asc~%%         (s$, pos&&)
declare sub      Beep
declare sub      BLoad          (file$)
declare sub      BLoad          (file$, offset%)
declare sub      BSave          (file$, offset%, length%)
declare sub      Chain          (file$)
declare sub      ChDir          (dir$)
declare function Chr$           (c%)
$syntax:[rel:"Step"](x, y), radius[, [drawColor][, [startRadian][, [stopRadian][, aspect]]]]
declare sub      Circle         (rel%, x!, y!, radius!, drawColor~&, startRadian!, stopRadian!, aspect!)
$syntax:[, [dataSize][, stackSize]]
declare sub      Clear          (dataSize&&, stackSize&&)
$syntax:[method][, [bgColor][, image]]
declare sub      Cls            (method%, bgColor~&, image&)
declare function Command$
declare function Command$       (n&)
declare function CsrLin&
declare function CVD#           (s$)
declare function CVDMBF#        (s$)
declare function CVI%           (s$)
declare function CVL&           (s$)
declare function CVS!           (s$)
declare function CVSMBF!        (s$)
declare function Date$
declare sub      Draw           (s$)
declare sub      Environ        (s$)
declare function Environ$       (s$)
declare function Environ$       (n&)
$syntax:([#]handle)
declare function Eof%%          (handle&)
declare function Erl&&
declare function Err%
declare sub      Error          (n%)
declare sub      Files
declare sub      Files          (fileSpec$)
declare function FreeFile&
declare function InStr&&        (haystack$, needle$)
declare function InStr&&        (start&&, haystack$, needle$)
declare function LCase$         (s$)
declare function Left$          (s$, i&&)
declare function Mid$           (s$, pos&&)
declare function Mid$           (s$, pos&&, length&&)
declare sub      MkDir          (path$)
declare sub      Out            (address%, value%)
declare function Right$         (s$, i&&)
declare function UCase$         (s$)
declare function Val##          (s$)
"""  # noqa: E501


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
