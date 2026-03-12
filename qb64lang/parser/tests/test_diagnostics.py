from .. import parse
from ..ast import If, Print
from ..diagnostics import E_UNEXPECTED_ITEM, E_UNKNOWN_CHARACTERS, lexpos2rowcol
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


def test_diags_in_order():
    prog = parse("x$ = 3 : print next")
    assert prog.diagnostics.diagnostics[0].startpos == 0
    assert prog.diagnostics.diagnostics[1].startpos == 15


def test_row_col():
    s = "abc\ndefg\n\nhijk"
    assert lexpos2rowcol(s, 0) == (1, 1)
    assert lexpos2rowcol(s, 1) == (1, 2)
    assert lexpos2rowcol(s, 3) == (1, 4)
    assert lexpos2rowcol(s, 6) == (2, 3)
    assert lexpos2rowcol(s, 8) == (2, 5)
    assert lexpos2rowcol(s, 9) == (3, 1)
