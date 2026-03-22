import contextlib
import os
from dataclasses import dataclass

from . import diagnostics as diag
from .ast import Node, SymbolStore
from .lexer import Lexer
from .ply import LexToken

TRACE_TOKENS = "TRACE_TOKENS" in os.environ


@dataclass
class _Flags:
    # '$dynamic, '$static
    dynamic_arrays: bool = False
    # Allow multiple procedures with same name
    allow_proc_overloads: bool = False
    # Mark procedures as builtin
    builtin: bool = False
    # Require stricter rules about sigil presence
    strictsigil: bool = False
    # Custom syntax spec in effect for next procedure
    syntax: str | None = None

    def set(self, key: str, value: str):
        match (key, value):
            case ("overload", "on"):
                self.allow_proc_overloads = True
            case ("overload", "off"):
                self.allow_proc_overloads = False
            case ("builtin", "on"):
                self.builtin = True
            case ("builtin", "off"):
                self.builtin = False
            case ("strictsigil", "on"):
                self.strictsigil = True
            case ("strictsigil", "off"):
                self.strictsigil = False


class NestList:
    def __init__(self):
        self.items = list[Node]()

    @contextlib.contextmanager
    def nest(self, item: Node):
        self.items.append(item)
        try:
            yield
        finally:
            self.items.pop()


class ParseContext:
    def __init__(self, input: str, symbols: SymbolStore, diags: diag.DiagnosticStore):
        self.diags = diags
        self.symbols = symbols
        self.token_stream = Lexer(self.symbols, self.diags)
        self.token_stream.input(input)
        self.reversed_tokens: list[LexToken] = []
        self._prev_prev = LexToken()
        self.prev = LexToken()
        self.tok: LexToken = LexToken()
        self.tok.lexer = self.token_stream
        self.tok.type = ""
        self.tok.value = ""
        # Any syntactic structures which can hold statements need to be
        # recorded here.
        self.nestings = NestList()
        self.flags = _Flags()

    def __next__(self):
        self._advance()
        while self.tok.type in ("META_CMD", "COMMENT"):
            if self.at_a("META_CMD"):
                self.do_metacommand()
            self._advance()
        return self.tok

    def _advance(self):
        self._prev_prev = self.prev
        self.prev = self.tok
        if len(self.reversed_tokens):
            self.tok = self.reversed_tokens.pop()
            if TRACE_TOKENS:
                print(">", self.tok)
            return
        try:
            self.tok = next(self.token_stream)
        except StopIteration:
            eof = LexToken()
            eof.lexer = self.tok.lexer
            eof.lexend = eof.lexpos = self.tok.lexer.lexlen
            eof.type = "EOF"
            eof.value = "<end of file>"
            eof.plain_value = eof.value
            self.tok = eof
        if TRACE_TOKENS:
            print(">", self.tok)
        return

    def reverse(self):
        if TRACE_TOKENS:
            print("<<<", self.tok)
        self.reversed_tokens.append(self.tok)
        self.tok = self.prev
        self.prev = self._prev_prev
        if TRACE_TOKENS:
            print(">", self.tok)

    def skip(self, type: str, value: str | None = None):
        while self.at_a(type, value):
            next(self)

    def consume(self, tok_type: str, tok_value: str | None = None):
        if tok_value is None:
            if self.tok.type != tok_type:
                self.diags.raise_error(
                    diag.E_UNEXPECTED_ITEM, self.tok, self.tok.type, tok_type
                )
        else:
            if self.tok.type != tok_type or self.tok.value != tok_value:
                self.diags.raise_error(
                    diag.E_UNEXPECTED_ITEM, self.tok, self.tok.value, tok_value
                )
        return next(self)

    def at_line_terminator(self):
        """
        Is current token a newline/:, else or EOF?
        """
        return self.at_a("NEWLINE") or self.at_a("KEYWORD", "else") or self.at_a("EOF")

    def at_a(self, type: str, value: str | None = None) -> bool:
        return self.tok.type == type and (value is None or self.tok.value == value)

    def was_at_a(self, type: str, value: str | None = None) -> bool:
        return self.prev.type == type and (value is None or self.prev.value == value)

    def drop_line(self):
        # This function must progress, so unconditionally drop the first token.
        at_line_terminator = self.at_line_terminator()
        with contextlib.suppress(diag.DiagnosticError):
            next(self)
        if at_line_terminator:
            return
        while not self.at_line_terminator():
            with contextlib.suppress(diag.DiagnosticError):
                next(self)

    def do_metacommand(self):
        match self.tok.value:
            case ("$dynamic", None):
                self.flags.dynamic_arrays = True
            case ("$static", None):
                self.flags.dynamic_arrays = False
            case ("$include", path):
                raise diag.ParseError(f"Unimplemented $include:'{path}'")
            case ("$flags", v):
                for item in v.split(","):
                    if "=" not in item:
                        self.diags.create(
                            diag.E_BAD_METACOMMAND, self.tok, "$flags:" + item
                        )
                        return
                    k, v = item.split("=", 1)
                    self.flags.set(k, v)
            case ("$syntax", syntax):
                self.flags.syntax = syntax
            case (name, None):
                self.diags.create(diag.E_BAD_METACOMMAND, self.tok, name)
            case (name, arg):
                self.diags.create(diag.E_BAD_METACOMMAND, self.tok, name + ":" + arg)
