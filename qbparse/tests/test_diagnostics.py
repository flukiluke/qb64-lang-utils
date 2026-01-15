from qbparse import parse
from qbparse.ast import Call, Constant, If, Print
from qbparse.datatypes import TYPE_INTEGER
from qbparse.diagnostics import E_UNEXPECTED_ITEM
from qbparse.tests.helpers import Ast, builtin_proc


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


def test_bad_stmt():
    prog = parse("""
        if x = 2 then
            "foo"
            ? 10 - 3
        end if
    """)
    assert prog.diagnostics.has(E_UNEXPECTED_ITEM)
    assert prog.main.find(If) == Ast(If, true_branch=[Ast(Print)])


def test_lex_range_leaf():
    assert Constant(42, TYPE_INTEGER, lex_start=7, lex_len=2).get_lex_range() == (7, 9)
    assert Constant(42, TYPE_INTEGER, lex_start=7).get_lex_range() == (7, 7)
    assert Constant(42, TYPE_INTEGER, lex_len=2).get_lex_range() is None
    assert Constant(42, TYPE_INTEGER).get_lex_range() is None


def test_lex_range_full_implicit():
    assert Call(
        builtin_proc("+"),
        [
            Constant(42, TYPE_INTEGER, lex_start=7, lex_len=2),
            Constant(420, TYPE_INTEGER, lex_start=11, lex_len=3),
        ],
    ).get_lex_range() == (7, 14)
    assert If(
        Constant(42, TYPE_INTEGER, lex_start=7, lex_len=2), [], [], []
    ).get_lex_range() == (7, 9)
    assert If(Constant(42, TYPE_INTEGER, lex_start=7), [], [], []).get_lex_range() == (
        7,
        7,
    )
    assert If(Constant(42, TYPE_INTEGER, lex_len=2), [], [], []).get_lex_range() is None
    assert If(Constant(42, TYPE_INTEGER), [], [], []).get_lex_range() is None


def test_lex_range_extension():
    assert Call(
        builtin_proc("+"),
        [
            Constant(42, TYPE_INTEGER, lex_start=7, lex_len=2),
            Constant(420, TYPE_INTEGER, lex_start=11, lex_len=3),
        ],
        lex_start=9,
        lex_len=1,
    ).get_lex_range() == (7, 14)
    assert Call(
        builtin_proc("+"),
        [
            Constant(42, TYPE_INTEGER, lex_start=7, lex_len=2),
            Constant(420, TYPE_INTEGER, lex_start=11, lex_len=3),
        ],
        lex_start=5,
        lex_len=1,
    ).get_lex_range() == (5, 14)
    assert Call(
        builtin_proc("+"),
        [
            Constant(42, TYPE_INTEGER, lex_start=7, lex_len=2),
            Constant(420, TYPE_INTEGER, lex_start=11, lex_len=3),
        ],
        lex_start=14,
        lex_len=1,
    ).get_lex_range() == (7, 15)

def test_msg():
    print(parse("x = if%").diagnostics.diagnostics)
    assert False