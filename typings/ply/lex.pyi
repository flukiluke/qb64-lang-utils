from collections.abc import Callable
from logging import Logger
from re import VERBOSE, Match, Pattern, RegexFlag
from typing import Any

class LexError(Exception):
    def __init__(self, message: str, s: str) -> None: ...

class LexToken:
    type: str
    value: Any
    lineno: int
    lexpos: int
    lexer: Lexer

    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...

class Lexer:
    lexpos: int
    lineno: int
    lexdata: str | bytes
    lexmatch: Match[str]

    def __init__(self) -> None: ...
    def clone(self, object: object) -> Lexer: ...
    def input(self, s: str | bytes) -> None: ...
    def begin(self, state: str) -> None: ...
    def push_state(self, state: str) -> None: ...
    def pop_state(self) -> None: ...
    def current_state(self) -> str: ...
    def skip(self, n: int) -> None: ...
    def token(self) -> LexToken | None: ...
    def __iter__(self) -> Lexer: ...
    def next(self) -> LexToken: ...

    __next__ = next

def lex(
    module: object | None = None,
    object: object | None = None,
    debug: bool = False,
    optimize: bool = False,
    lextab: str = "lextab",
    reflags: int | RegexFlag = int(VERBOSE),
    nowarn: bool = False,
    outputdir: str | None = None,
    debuglog: Logger | None = None,
    errorlog: Logger | None = None,
) -> Lexer: ...
def runmain(lexer: Lexer | None, data: str | bytes | None) -> None: ...

_TokenFunction = Callable[[LexToken], LexToken | None]

def TOKEN(r: str | Pattern[str]) -> Callable[[_TokenFunction], _TokenFunction]: ...

Token = TOKEN
