from .. import diagnostics as diag
from .. import parse
from ..ast import Assignment, Print
from .helpers import Ast, parse_clean


def test_line_split():
    assert parse_clean("x = 3 : print x").main.statements == [
        Ast(Assignment),
        Ast(Print),
    ]


def test_newline_required():
    assert parse("x = 3 print x").diagnostics.has(diag.E_UNEXPECTED_ITEM)
    assert parse("while x : wend a = 1").diagnostics.has(diag.E_UNEXPECTED_ITEM)
