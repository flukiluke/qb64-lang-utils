from pytest import raises

from qbparse import parse
from qbparse.ast import Constant, If, Print, Statement
from qbparse.datatypes import BUILTIN_TYPES
from qbparse.errors import ParseError

SINGLE = BUILTIN_TYPES["single"]
STRING = BUILTIN_TYPES["string"]
ONE = Constant(1, SINGLE)
TWO = Constant(2, SINGLE)
THREE = Constant(3, SINGLE)


def PrintStr(s: str):
    return Print([Constant(s, STRING)])


def run(input: str):
    program = parse(input)
    impl = program.globals.procedures["_main"].impl
    assert impl is not None
    return impl


def test_single_line():
    stmts = list(run('if 1 then print "a";\nif 1 then print "b";').find_all(If))
    assert stmts == [
        If(
            ONE,
            [PrintStr("a")],
            [],
            [],
        ),
        If(
            ONE,
            [PrintStr("b")],
            [],
            [],
        ),
    ]


def test_double_else():
    raises(ParseError, parse, 'if 1 then print "a"; else print "b"; else print "c";')


def test_single_line_else():
    stmts = list(
        run('if 1 then print "x"; else print "y";\nprint 2;').find_all(Statement)
    )
    assert stmts == [
        If(
            ONE,
            [PrintStr("x")],
            [],
            [PrintStr("y")],
        ),
        Print([TWO]),
    ]


def test_trailing_else():
    stmts = list(run('if 1 then print "x"; else\nprint "y";').find_all(Statement))
    assert stmts == [
        If(
            ONE,
            [PrintStr("x")],
            [],
            [],
        ),
        PrintStr("y"),
    ]


def test_multi_line():
    stmts = list(
        run("""
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
""").find_all(Statement)
    )
    assert stmts == [
        If(
            ONE,
            [PrintStr("x"), PrintStr("y")],
            [],
            [],
        ),
        If(
            ONE,
            [PrintStr("a")],
            [],
            [PrintStr("b"), PrintStr("c")],
        ),
        If(
            ONE,
            [],
            [],
            [PrintStr("d")],
        ),
        If(
            ONE,
            [PrintStr("e")],
            [],
            [],
        ),
    ]


def test_elseif():
    stmts = list(
        run("""
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
    """).find_all(Statement)
    )
    assert stmts == [
        If(
            ONE,
            [PrintStr("a")],
            [(TWO, [PrintStr("b")])],
            [],
        ),
        If(
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
        ),
    ]


def test_else_last():
    raises(
        ParseError,
        parse,
        """
        if 1 then
            print "a"
        else
            print "b"
        elseif 1 then
            print "c"
    """,
    )


def test_single_line_colons():
    stmts = list(
        run("""
            if 1 then print "a";:print "b";
            if 1 then :
            if 1 then :print "c";:
            if 1 then :print "d";:print "e";
            if 1 then print "f"; else :
            if 1 then print "g"; else print "h"; :print "i";
            if 1 then print "j"; else :print "k";:
    """).find_all(Statement)
    )
    assert stmts == [
        If(ONE, [PrintStr("a"), PrintStr("b")], [], []),
        If(ONE, [], [], []),
        If(ONE, [PrintStr("c")], [], []),
        If(ONE, [PrintStr("d"), PrintStr("e")], [], []),
        If(ONE, [PrintStr("f")], [], []),
        If(ONE, [PrintStr("g")], [], [PrintStr("h"), PrintStr("i")]),
        If(ONE, [PrintStr("j")], [], [PrintStr("k")]),
    ]


def test_rem():
    stmts = list(
        run("""
            if 1 then rem
            if 1 then
                print "a";
            else rem
            end if
            if 1 then
            else rem
                print "b";
            end if
            """).find_all(Statement)
    )
    assert stmts == [
        If(ONE, [], [], []),
        If(ONE, [PrintStr("a")], [], []),
        If(ONE, [], [], [PrintStr("b")]),
    ]


def test_nested_if():
    stmts = list(
        run("""
            if 1 then
                print "a";
                if 2 then
                    print "b";
                else
                    print "c";
                end if
            elseif 2 then if 3 then print "d";
            end if
            """).find_all(Statement)
    )
    assert stmts == [
        If(
            ONE,
            [
                PrintStr("a"),
                If(TWO, [PrintStr("b")], [], [PrintStr("c")]),
            ],
            [(TWO, [If(THREE, [PrintStr("d")], [], [])])],
            [],
        )
    ]


# TODO: IF x THEN 100 ELSE 200
