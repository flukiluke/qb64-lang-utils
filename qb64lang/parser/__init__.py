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
$syntax:[fg][, [bg][, [border][, image]]]
declare sub      Color          (fg~&, bg~&, border~&, image&)
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
declare function InKey$
declare function Inp%           (address%)
declare function Input$         (bytes&&)
declare function Input$         (bytes&&, file&)
declare function InStr&&        (haystack$, needle$)
declare function InStr&&        (start&&, haystack$, needle$)
declare sub      Kill           (file$)
declare function LCase$         (s$)
declare function Left$          (s$, i&&)
declare function Loc&&          (file&)
$syntax:[row][, [column][, [cursor][, [cursorStart][, cursorEnd]]]]
declare sub      Locate         (row%, column%, cursor%, cursorStart%, cursorEnd%)
$syntax:([#]handle)
declare function Lof&&          (handle&)
declare function LPos%          (index%)
declare function LTrim$         (s$)
declare function Mid$           (s$, pos&&)
declare function Mid$           (s$, pos&&, length&&)
declare function MKD$           (n#)
declare function MKDMBF$        (n#)
declare function MKI$           (n%)
declare function MKL$           (n&)
declare function MKS$           (n!)
declare function MKSMBF$        (n!)
declare sub      MkDir          (path$)
$syntax:old "AS" new
declare sub      Name           (old$, new$)
declare sub      Out            (address%, value%)
$syntax:[rel:"Step"](x, y), fillColor[, borderColor]
declare sub      Paint          (rel%, x!, y!, fillColor~&, borderColor~&)
declare sub      Palette
declare sub      Palette        (attribute%, mapColor~&)
declare sub      PCopy          (source%, dest%)
declare function Peek%%         (address%)
$syntax:voice1[, [voice2][, [voice3][, voice4]]]
declare sub      Play           (voice1$, voice2$, voice3$, voice4$)
declare function Play#
declare function Play#          (voice&)
declare function PMap!          (value!, action%)
declare function Point!         (action%)
declare function Point~&        (x!, y!)
declare sub      Poke           (address%, value%)
declare function Pos%           (dummy&)
$syntax:[rel:"Step"](x, y)[, setColor]
declare sub      PReset         (rel%, x!, y!, setColor~&)
$syntax:[rel:"Step"](x, y)[, setColor]
declare sub      PSet           (rel%, x!, y!, setColor~&)
declare sub      Reset
declare function Right$         (s$, i&&)
declare sub      RmDir          (dir$)
declare function Rnd!
declare function Rnd!           (n!)
declare function RTrim$         (s$)
declare function SAdd%          (s$)
declare function Screen~&       (row%, col%)
declare function Screen~&       (row%, col%, colorFlag%)
declare sub      Seek           (handle&, position&&)
declare function Seek&&         (handle&)
declare function Shell%%        (cmd$)
declare sub      Sleep
declare sub      Sleep          (seconds&)
declare function Space$         (count&&)
declare function Stick%         (direction%)
declare function Stick%         (direction%, axis%)
declare sub      Stop
$syntax: (button[, device]) action:{"On" | "Off" | "Stop"}
declare sub      STrig          (button%, device%, action%)
declare function String$        (count&&, character$)
declare function String$        (count&&, byte%%)
declare sub      System         (code%)
declare function Time$
declare function Timer!
declare function Timer#         (accuracy!)
declare function UCase$         (s$)
$syntax:[#]handle[, [firstRecord] ["To" lastRecord]]
declare sub      Unlock         (handle&, firstRecord&&, lastRecord&&)
$syntax:[[isScreen:"Screen"] (x1, y1)-(x2, y2)[, [bgColor][, borderColor]]]
declare sub      View           (isScreen%, x1!, y1!, x2!, y2!, bgColor~&, borderColor~&)
declare sub      Wait           (port%, andMask%)
declare sub      Wait           (port%, andMask%, xorMask%)
$syntax:[[isScreen:"Screen"] (x1, y1)-(x2, y2)]
declare sub      Window         (isScreen%, x1!, y1!, x2!, y2!)
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
