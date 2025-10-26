from collections.abc import Iterable

from ast_nodes import Procedure, Statement
from datatypes import TypeSignature
from lexer import Lexer
from symbols import BUILTIN_TYPES, SymbolStore


class EndOfBlock(Exception):
    pass


class Parser:
    def __init__(self, input: str):
        self.symbols = SymbolStore()
        self.token_stream = Lexer(self.symbols)
        self.token_stream.input(input)
        self.tok = next(self.token_stream)

    def parse(self):
        main = Procedure("_main", TypeSignature(BUILTIN_TYPES["_none"], []))
        main.children.extend(self._do_block())

    def _toknext(self):
        self.tok = next(self.token_stream)
        return self.tok

    def _skip(self, *tok_types: str):
        while self.tok.type in tok_types:
            self._toknext()

    def _startline(self):
        self._skip("NEWLINE", "LINE_SPLIT")

    def _do_block(self) -> Iterable[Statement]:
        stmts: list[Statement] = []
        while True:
            try:
                stmt = self._do_stmt()
                if stmt is not None:
                    stmts.append(stmt)
            except EndOfBlock:
                return stmts

    def _do_stmt(self) -> Statement | None:
        self._startline()
