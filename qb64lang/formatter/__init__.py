import contextlib
import re
from enum import Enum, auto

from ..parser import Program
from ..parser.ast import KEYWORDS, Procedure, SymbolStore, Variable
from ..parser.datatypes import Type
from ..parser.diagnostics import DiagnosticError, DiagnosticStore
from ..parser.lexer import Lexer
from ..parser.ply import LexToken


class Capitalisation(Enum):
    NONE = auto()
    CAMEL = auto()
    UPPER = auto()


class FormatContext:
    def __init__(self, input: str, symbols: SymbolStore, caps_style: Capitalisation):
        self.diags = DiagnosticStore()
        self.tok: LexToken = LexToken()
        self.symbols = symbols
        self.token_stream = Lexer(self.symbols, self.diags)
        self.caps_style = caps_style
        self.result = ""
        self.at_statment_position = True
        self.at_flex_space = False
        self.token_stream.input(input)
        next(self)

    def __next__(self):
        try:
            self.tok = next(self.token_stream)
        except StopIteration:
            eof = LexToken()
            eof.lexer = self.tok.lexer
            eof.lexpos = self.tok.lexer.lexlen
            eof.length = 0
            eof.type = "EOF"
            eof.value = "<end of file>"
            self.tok = eof
        return self.tok

    def at_a(self, type: str, value: str | None = None) -> bool:
        return self.tok.type == type and (value is None or self.tok.value == value)

    def at_line_terminator(self):
        """
        Is current token a newline/:, else or EOF?
        """
        return self.at_a("NEWLINE") or self.at_a("KEYWORD", "else") or self.at_a("EOF")

    def case(self, camel: str, actual: str):
        if self.caps_style == Capitalisation.UPPER:
            return camel.upper()
        if self.caps_style == Capitalisation.CAMEL:
            return camel
        return actual

    def add(self, text: str):
        if self.at_flex_space:
            self.result += " "
            self.at_flex_space = False
        self.result += text
        self.at_statment_position = False

    def newline(self):
        self.result += "\n"
        self.at_statment_position = True
        self.at_flex_space = False

    def pre_flex(self):
        if not self.at_statment_position:
            self.at_flex_space = True

    def post_flex(self):
        self.at_flex_space = True

    def no_flex(self):
        self.at_flex_space = False

    def statement_position(self):
        self.at_statment_position = True


def format(program: Program, caps_style: Capitalisation = Capitalisation.UPPER):
    ctx = FormatContext(program.input, program.symbols, caps_style)
    while not ctx.at_a("EOF"):
        match (ctx.tok.type, ctx.tok.value):
            case ("NEWLINE", "rem"):
                ctx.pre_flex()
                ctx.add(
                    ctx.case("Rem", ctx.tok.plain_value[:3]) + ctx.tok.plain_value[3:]
                )
            case ("NEWLINE", "'"):
                ctx.pre_flex()
                ctx.add(ctx.tok.plain_value)
            case ("NEWLINE", ":"):
                ctx.no_flex()
                ctx.add(":")
                ctx.post_flex()
                ctx.statement_position()
            case ("NEWLINE", "\n"):
                ctx.newline()
            case ("KEYWORD", keyword):
                assert isinstance(keyword, str)
                ctx.pre_flex()
                ctx.add(ctx.case(KEYWORDS[keyword], ctx.tok.plain_value))
                ctx.post_flex()
            case ("VARIABLE", var):
                assert isinstance(var, Variable)
                name, _ = _split_name_sigil(var.source_name)
                _, sigil = _split_name_sigil(ctx.tok.plain_value)
                ctx.add(name + sigil)
            case ("PROCEDURE", proc):
                assert isinstance(proc, Procedure)
                name, _ = _split_name_sigil(proc.source_name)
                _, sigil = _split_name_sigil(ctx.tok.plain_value)
                stmt = ctx.at_statment_position
                ctx.add(name + sigil)
                if stmt:
                    ctx.post_flex()
            case ("TYPE", type):
                assert isinstance(type, Type)
                ctx.pre_flex()
                ctx.add(ctx.case(type.name, ctx.tok.plain_value))
                ctx.post_flex()
            case ("STRING_LIT", text):
                assert isinstance(text, str)
                ctx.add('"' + text + '"')
            case ("NUM_LIT", (value, type)):
                ctx.add(str(value))
            case ("PUNCTUATION", "(" | ")" as c):
                assert isinstance(c, str)
                ctx.add(c)
            case ("PUNCTUATION", c):
                assert isinstance(c, str)
                ctx.pre_flex()
                ctx.add(c)
                ctx.post_flex()
        with contextlib.suppress(DiagnosticError):
            next(ctx)
    return ctx.result


def _split_name_sigil(s: str):
    match = re.match(r"([a-z0-9_.]+)(.*)", s, re.IGNORECASE)
    assert match is not None
    return match.group(1, 2)
