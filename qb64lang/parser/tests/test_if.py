from .. import diagnostics as diag
from .. import parse
from ..ast import Constant, If, Print, Statement
from ..datatypes import TYPE_INTEGER, TYPE_STRING
from .helpers import Ast, parse_clean

ONE = Ast(Constant, 1, TYPE_INTEGER)
TWO = Ast(Constant, 2, TYPE_INTEGER)
THREE = Ast(Constant, 3, TYPE_INTEGER)


def PrintStr(s: str):
    return Ast(Print, [Ast(Constant, s, TYPE_STRING), Print.Element.SEMICOLON])


def test_single_line():
    stmts = list(
        parse_clean('if 1 then print "a";\nif 1 then print "b";').main.find_all(If)
    )
    assert stmts == [
        Ast(If, ONE, [PrintStr("a")], [], [], is_single_line=True),
        Ast(If, ONE, [PrintStr("b")], [], [], is_single_line=True),
    ]


def test_double_else():
    prog = parse('if 1 then print "a"; else print "b"; else print "c";')
    assert prog.diagnostics.has(diag.E_UNEXPECTED_KEYWORD)


def test_single_line_else():
    stmts = list(
        parse_clean('if 1 then print "x"; else print "y";\nprint 2').main.find_all(
            Statement
        )
    )
    assert stmts == [
        Ast(If, ONE, [PrintStr("x")], [], [PrintStr("y")], is_single_line=True),
        Ast(Print, [TWO]),
    ]


def test_trailing_else():
    stmts = list(
        parse_clean('if 1 then print "x"; else\nprint "y";').main.find_all(Statement)
    )
    assert stmts == [
        Ast(If, ONE, [PrintStr("x")], [], [], is_single_line=True),
        PrintStr("y"),
    ]


def test_multi_line():
    stmts = list(
        parse_clean("""
            if 1 then
                print "x";
                print "y";
            end if
            if 1 then
                print "a";
            else print "b";
                print "c";
            end if
            if 1 then
            else
                print "d";
            endif
            if 1 then
                print "e";
            else
            end if
""").main.find_all(Statement)
    )
    assert stmts == [
        Ast(If, ONE, [PrintStr("x"), PrintStr("y")], [], [], is_single_line=False),
        Ast(
            If,
            ONE,
            [PrintStr("a")],
            [],
            [PrintStr("b"), PrintStr("c")],
            is_single_line=False,
        ),
        Ast(If, ONE, [], [], [PrintStr("d")], is_single_line=False),
        Ast(If, ONE, [PrintStr("e")], [], [], is_single_line=False),
    ]


def test_elseif():
    stmts = list(
        parse_clean("""
            if 1 then
                print "a";
            elseif 2 then
                print "b";
            end if
            if 1 then
            elseif 2 then print "c";
            elseif 3 then print "d";
                print "e";
            else
                print "f";
            endif
    """).main.find_all(Statement)
    )
    assert stmts == [
        Ast(
            If, ONE, [PrintStr("a")], [(TWO, [PrintStr("b")])], [], is_single_line=False
        ),
        Ast(
            If,
            ONE,
            [],
            [
                (TWO, [PrintStr("c")]),
                (
                    THREE,
                    [
                        PrintStr("d"),
                        PrintStr("e"),
                    ],
                ),
            ],
            [PrintStr("f")],
            is_single_line=False,
        ),
    ]


def test_else_last():
    prog = parse(
        """
        if 1 then
            print "a"
        else
            print "b"
        elseif 1 then
            print "c"
    """,
    )
    assert prog.diagnostics.has(diag.E_UNEXPECTED_ITEM)


def test_single_line_colons():
    stmts = list(
        parse_clean("""
            if 1 then print "a";:print "b";
            if 1 then :
            if 1 then :print "c";:
            if 1 then :print "d";:print "e";
            if 1 then print "f"; else :
            if 1 then print "g"; else print "h"; :print "i";
            if 1 then print "j"; else :print "k";:
    """).main.find_all(Statement)
    )
    assert stmts == [
        Ast(If, ONE, [PrintStr("a"), PrintStr("b")], [], [], is_single_line=True),
        Ast(If, ONE, [], [], [], is_single_line=True),
        Ast(If, ONE, [PrintStr("c")], [], [], is_single_line=True),
        Ast(If, ONE, [PrintStr("d"), PrintStr("e")], [], [], is_single_line=True),
        Ast(If, ONE, [PrintStr("f")], [], [], is_single_line=True),
        Ast(
            If,
            ONE,
            [PrintStr("g")],
            [],
            [PrintStr("h"), PrintStr("i")],
            is_single_line=True,
        ),
        Ast(If, ONE, [PrintStr("j")], [], [PrintStr("k")], is_single_line=True),
    ]


def test_rem():
    stmts = list(
        parse_clean("""
            if 1 then rem
            if 1 then
                print "a";
            else rem
            end if
            if 1 then
            else rem
                print "b";
            end if
            """).main.find_all(Statement)
    )
    assert stmts == [
        Ast(If, ONE, [], [], [], is_single_line=True),
        Ast(If, ONE, [PrintStr("a")], [], [], is_single_line=False),
        Ast(If, ONE, [], [], [PrintStr("b")], is_single_line=False),
    ]


def test_nested_if():
    stmts = list(
        parse_clean("""
            if 1 then
                print "a";
                if 2 then
                    print "b";
                else
                    print "c";
                end if
            elseif 2 then if 3 then print "d";
            end if
            """).main.find_all(Statement)
    )
    assert stmts == [
        Ast(
            If,
            ONE,
            [
                PrintStr("a"),
                Ast(If, TWO, [PrintStr("b")], [], [PrintStr("c")]),
            ],
            [(TWO, [Ast(If, THREE, [PrintStr("d")], [], [])])],
            [],
        )
    ]


def test_bad_guard():
    assert parse('if "foo" then print "bar"').diagnostics.has(
        diag.E_NON_NUMERIC_CONDITION
    )
    assert parse("""
            if 1 then
                print "hi"
            elseif "foo" then
                print "bar"
            end if
            """).diagnostics.has(diag.E_NON_NUMERIC_CONDITION)


# TODO: IF x THEN 100 ELSE 200
# TODO: IF x GOTO label
