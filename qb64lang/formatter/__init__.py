import contextlib
import re
from collections.abc import Generator
from enum import Enum, auto

from qb64lang.parser.ast import Call

from ..parser import Program
from ..parser.ast import (
    KEYWORDS,
    FieldAccess,
    If,
    Node,
    Procedure,
    Variable,
)
from ..parser.datatypes import Type
from ..parser.diagnostics import DiagLevel, DiagnosticError, DiagnosticStore
from ..parser.lexer import Id, Lexer
from ..parser.ply import LexToken


class Capitalisation(Enum):
    NONE = auto()
    CAMEL = auto()
    UPPER = auto()


class FormatContext:
    def __init__(self, program: Program, caps_style: Capitalisation, indent_size: int):
        self.diags = DiagnosticStore()
        self.tok: LexToken = LexToken()
        self.symbols = program.symbols
        self.token_stream = Lexer(self.symbols, self.diags)
        self.caps_style = caps_style
        self.indent_size = indent_size
        self.result = ""
        self.at_statment_position = True
        self.at_flex_space = False
        self.at_force_stick = False
        self.ast_walker = _ast_walk(program.main, 0, program.main)
        self.node = next(self.ast_walker)
        self.main = program.main
        self.input = program.input
        self.token_stream.input(program.input)
        self.error_locations = [
            (d.startpos, d.endpos)
            for d in program.diagnostics.diagnostics
            if d.template.level == DiagLevel.ERR_SYN
        ]
        self.error_index = 0
        self.indent_level = 0

    def advance(self):
        try:
            next(self)
        except DiagnosticError as e:
            self.tok = e.source
            self.skip_line()
            return
        while self.error_index < len(self.error_locations):
            err = self.error_locations[self.error_index]
            pos = self.tok.lexpos
            if pos < err[0]:
                return
            elif err[0] <= pos < err[1]:
                self.skip_line()
                return
            else:
                self.error_index += 1

    def __next__(self):
        try:
            self.tok = next(self.token_stream)
        except StopIteration:
            eof = LexToken()
            eof.lexer = self.tok.lexer
            eof.lexend = eof.lexpos = self.tok.lexer.lexlen
            eof.type = "EOF"
            eof.value = "<end of file>"
            self.tok = eof
        try:
            self.node = self.ast_walker.send(self.tok.lexpos)
        except StopIteration:
            self.node = self.main
        return self.tok

    def skip_line(self):
        # Rewind to start of line
        input_start = self.input.rfind("\n", 0, self.tok.lexpos) + 1
        self.result = self.result[: self.result.rfind("\n") + 1]
        # Find next newline
        with contextlib.suppress(DiagnosticError):
            next(self)
        while not self.at_a("NEWLINE", "\n") and not self.at_a("EOF"):
            with contextlib.suppress(DiagnosticError):
                next(self)
        self.result += self.input[input_start : self.tok.lexpos]

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
        if len(self.result) and self.result[-1] == "\n":
            self.result += " " * (self.indent_level * self.indent_size)
        elif self.at_flex_space and not self.at_force_stick:
            self.result += " "
        self.at_flex_space = False
        self.at_force_stick = False
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

    def force_stick(self):
        self.at_force_stick = True

    def statement_position(self):
        self.at_statment_position = True

    def indent(self):
        self.indent_level += 1

    def outdent(self, n: int = 1):
        self.indent_level = max(0, self.indent_level - n)


def format(
    program: Program,
    caps_style: Capitalisation = Capitalisation.UPPER,
    indent_size: int = 4,
):
    ctx = FormatContext(program, caps_style, indent_size)
    ctx.advance()
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
                _format_keyword(ctx, keyword)
            case ("VARIABLE", var):
                assert isinstance(var, Variable)
                name, _ = _split_name_sigil(var.source_name)
                _, sigil = _split_name_sigil(ctx.tok.plain_value)
                ctx.add(name + sigil)
            case ("PROCEDURE", proc):
                assert isinstance(proc, Procedure)
                name, _ = _split_name_sigil(proc.source_name)
                used_name, sigil = _split_name_sigil(ctx.tok.plain_value)
                stmt = ctx.at_statment_position
                if proc.builtin:
                    ctx.add(ctx.case(name, used_name) + sigil)
                else:
                    ctx.add(name)
                if stmt:
                    ctx.post_flex()
            case ("TYPE", type):
                assert isinstance(type, Type)
                ctx.pre_flex()
                if type.is_builtin():
                    ctx.add(ctx.case(type.source_name, ctx.tok.plain_value))
                else:
                    ctx.add(type.source_name)
                ctx.post_flex()
            case ("ID", c):
                assert isinstance(c, Id)
                ctx.add(ctx.tok.plain_value)
                if c.sigil is not None:
                    ctx.add(c.sigil)
            case ("DOTTED_ID", _):
                if isinstance(ctx.node, FieldAccess):
                    ctx.add(".")
                    ctx.add(ctx.node.field.source_name)
                else:
                    # Not expected to occur
                    ctx.add(ctx.tok.plain_value)
            case ("STRING_LIT", text):
                assert isinstance(text, str)
                ctx.add('"' + text + '"')
            case ("NUM_LIT", _):
                ctx.add(ctx.tok.plain_value.upper())
            case ("PUNCTUATION", "+"):
                if not (
                    isinstance(ctx.node, Call)
                    and ctx.node.impl
                    and len(ctx.node.impl.signature.params) == 1
                ):
                    ctx.pre_flex()
                    ctx.add("+")
                    ctx.post_flex()
            case ("PUNCTUATION", "-"):
                ctx.pre_flex()
                ctx.add("-")
                if (
                    isinstance(ctx.node, Call)
                    and ctx.node.impl
                    and len(ctx.node.impl.signature.params) == 1
                ):
                    ctx.force_stick()
                else:
                    ctx.post_flex()
            case ("PUNCTUATION", "(" | ")" as c):
                assert isinstance(c, str)
                ctx.add(c)
            case ("PUNCTUATION", ","):
                ctx.add(",")
                ctx.post_flex()
            case ("PUNCTUATION", c):
                assert isinstance(c, str)
                ctx.pre_flex()
                ctx.add(c)
                ctx.post_flex()
        ctx.advance()
    return ctx.result


def _format_keyword(ctx: FormatContext, keyword: str):
    statement = ctx.at_statment_position
    if statement:
        _handle_indent_before(ctx, keyword)
    ctx.pre_flex()
    ctx.add(ctx.case(KEYWORDS[keyword], ctx.tok.plain_value))
    ctx.post_flex()
    if statement:
        _handle_indent_after(ctx, keyword)


def _handle_indent_before(ctx: FormatContext, keyword: str):
    match keyword:
        case "elseif" | "endif" | "loop" | "wend":
            ctx.outdent()
        case "else":
            if isinstance(ctx.node, If) and not ctx.node.is_single_line:
                ctx.outdent()
        case "next":
            # Check for NEXT j, i style
            i = ctx.tok.lexpos
            while i < len(ctx.input) and re.match(r"[a-zA-Z0-9 \t,]", ctx.input[i]):
                i += 1
            line = ctx.input[ctx.tok.lexpos : i]
            ctx.outdent(line.count(",") + 1)
        case "case":
            pass
        case "end":
            if not isinstance(ctx.node, Call):
                # Ignore END command
                ctx.outdent()


def _handle_indent_after(ctx: FormatContext, keyword: str):
    match keyword:
        case "do" | "for" | "while" | "select" | "type" | "sub" | "function":
            ctx.indent()
        case "if" | "elseif" | "else":
            if isinstance(ctx.node, If) and not ctx.node.is_single_line:
                ctx.indent()
        case "case":
            pass


def _split_name_sigil(s: str):
    match = re.match(r"([a-z0-9_.]+)(.*)", s, re.IGNORECASE)
    assert match is not None
    return match.group(1, 2)


def _ast_walk(node: Node, target_pos: int, parent: Node) -> Generator[Node, int, int]:
    while True:
        if target_pos < node.lex_start:
            target_pos = yield parent
        elif node.lex_end <= target_pos:
            return target_pos
        else:
            for child in node.children():
                target_pos = yield from _ast_walk(child, target_pos, node)
            if target_pos < node.lex_end:
                target_pos = yield node
