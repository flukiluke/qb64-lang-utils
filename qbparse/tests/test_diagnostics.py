from qbparse import parse
from qbparse.ast import If, Print
from qbparse.diagnostics import E_UNEXPECTED_ITEM
from qbparse.tests.helpers import Ast


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
