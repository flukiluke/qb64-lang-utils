from pytest import raises

from qbparse import parse
from qbparse.ast import Call, Constant, Loop, Print
from qbparse.errors import ParseError
from qbparse.tests.helpers import Ast, builtin_proc


def test_do_while():
    loop = parse(
        """
        do while x > 1
            print "hi"
        loop
    """
    ).main.find(Loop)
    assert loop == Ast(Loop, Ast(Call, builtin_proc(">")), [Ast(Print)], top_check=True)


def test_do_until():
    loop = parse(
        """
        do until x > 1
            print "hi"
        loop
    """
    ).main.find(Loop)
    assert loop == Ast(
        Loop,
        Ast(Call, builtin_proc("<>"), [Ast(Call, builtin_proc(">")), Ast(Constant, 0)]),
        [Ast(Print)],
        top_check=True,
    )


def test_loop_while():
    loop = parse(
        """
        do
            print "hi"
        loop while x > 1
    """
    ).main.find(Loop)
    assert loop == Ast(
        Loop, Ast(Call, builtin_proc(">")), [Ast(Print)], top_check=False
    )


def test_loop_until():
    loop = parse(
        """
        do
            print "hi"
        loop until x > 1
    """
    ).main.find(Loop)
    assert loop == Ast(
        Loop,
        Ast(Call, builtin_proc("<>"), [Ast(Call, builtin_proc(">")), Ast(Constant, 0)]),
        [Ast(Print)],
        top_check=False,
    )


def test_infinite_loop():
    loop = parse(
        """
        do:print "hi"
        loop
        """
    ).main.find(Loop)
    assert loop == Ast(Loop, Ast(Constant, 1), [Ast(Print)])


def test_while():
    loop = parse(
        """
        while x > 1
            print "hi"
        wend
    """
    ).main.find(Loop)
    assert loop == Ast(Loop, Ast(Call, builtin_proc(">")), [Ast(Print)], top_check=True)


def test_empty_loop():
    loop = parse("while x > 1:wend").main.find(Loop)
    assert loop == Ast(Loop, Ast(Call, builtin_proc(">")), [], top_check=True)


def test_nested_loop():
    loop = parse(
        """
        do while x > 1
            do
                print "hi"
            loop while f < 3
        loop
        """
    ).main.find(Loop)
    assert loop == Ast(
        Loop,
        Ast(Call, builtin_proc(">")),
        [Ast(Loop, Ast(Call, builtin_proc("<")), [Ast(Print)], top_check=False)],
        top_check=True,
    )


def test_loop_string_guard():
    assert len(parse('while "foo": wend').errors) > 0


def test_multi_guard():
    raises(
        ParseError,
        parse,
        """
        do while x > 1
        loop until x > 1
    """,
    )


def test_missing_guard():
    raises(
        ParseError,
        parse,
        """
        while
           print "hi"
        wend
    """,
    )
