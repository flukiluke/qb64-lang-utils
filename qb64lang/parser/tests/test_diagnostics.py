from .. import parse
from ..ast import If, Print
from ..diagnostics import E_UNEXPECTED_ITEM, E_UNKNOWN_CHARACTERS
from .helpers import Ast


def test_bad_expr_drops_line():
    prog = parse("""
        if x = 2 then
            ? 23 * 1
            ? 2 + / 2
            ? 10 - 3
        end if
    """)
    assert prog.diagnostics.has(E_UNEXPECTED_ITEM)
    assert prog.main.find(If) == Ast(If, true_branch=[Ast(Print), Ast(Print)])


def test_double_fault():
    prog = parse("print !@foo")
    assert prog.diagnostics.has(E_UNKNOWN_CHARACTERS)


def test_bad_stmt():
    prog = parse("""
        if x = 2 then
            "foo"
            ? 10 - 3
        end if
    """)
    assert prog.diagnostics.has(E_UNEXPECTED_ITEM)
    assert prog.main.find(If) == Ast(If, true_branch=[Ast(Print)])
