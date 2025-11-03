import os

from ply.lex import LexToken

from qbparse.errors import ParseError
from qbparse.lexer import Lexer
from qbparse.symbols import SymbolStore

TRACE_TOKENS = "TRACE_TOKENS" in os.environ


class ParseContext:
    def __init__(self, input: str, symbols: SymbolStore):
        self.symbols = symbols
        self.token_stream = Lexer(self.symbols)
        self.token_stream.input(input)
        self.reversed_tokens: list[LexToken] = []
        next(self)

    def __next__(self):
        if len(self.reversed_tokens):
            self.tok = self.reversed_tokens.pop()
            if TRACE_TOKENS:
                print(">", self.tok)
            return self.tok
        try:
            self.tok = next(self.token_stream)
        except StopIteration:
            eof = LexToken()
            eof.lexer = self.tok.lexer
            eof.lexpos = self.tok.lexer.lexlen
            eof.lineno = self.tok.lineno
            eof.type = "EOF"
            eof.value = ""
            self.tok = eof
        if TRACE_TOKENS:
            print(">", self.tok)
        return self.tok

    def reverse(self, tok: LexToken):
        if TRACE_TOKENS:
            print("<<<", self.tok)
        self.reversed_tokens.append(self.tok)
        self.tok = tok
        if TRACE_TOKENS:
            print(">", self.tok)

    def skip(self, type: str, value: str | None = None):
        while self.at_a(type, value):
            next(self)

    def consume(self, tok_type: str, tok_value: str | None = None):
        if tok_value is None:
            if self.tok.type != tok_type:
                raise ParseError("Expected " + tok_type)
        else:
            if self.tok.type != tok_type and self.tok.value != tok_value:
                raise ParseError(f"Expected {tok_type} {tok_value}")
        return next(self)

    def at_line_terminator(self):
        """
        Is current token a newline/:, else or EOF?
        """
        return self.at_a("NEWLINE") or self.at_a("KEYWORD", "else") or self.at_a("EOF")

    def at_a(self, type: str, value: str | None = None) -> bool:
        return self.tok.type == type and (value is None or self.tok.value == value)
