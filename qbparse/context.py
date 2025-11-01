from ply.lex import LexToken

from qbparse.errors import ParseError
from qbparse.lexer import Lexer
from qbparse.symbols import SymbolStore


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
        return self.tok

    def reverse(self, tok: LexToken):
        self.reversed_tokens.append(self.tok)
        self.tok = tok

    def skip(self, *tok_types: str):
        while self.tok.type in tok_types:
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
        return (
            self.at_a("NEWLINE")
            or self.at_a("LINE_SPLIT")
            or self.at_a("KEYWORD", "else")
            or self.at_a("EOF")
        )

    def at_a(self, type: str, value: str | None = None):
        return self.tok.type == type and (value is None or self.tok.value == value)
