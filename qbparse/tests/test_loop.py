import qbparse.diagnostics as diag
from qbparse import parse
from qbparse.ast import Call, Constant, Loop, Print
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
    assert parse('while "foo": wend').diagnostics.has(diag.E_NON_NUMERIC_CONDITION)


def test_multi_guard():
    prog = parse("""
        do while x > 1
            print "hi"
        loop until x > 1
    """)
    assert prog.diagnostics.has(diag.E_TOO_MANY_LOOP_GUARDS)
    assert prog.main.find(Loop) == Ast(Loop, Ast(Call), [Ast(Print)], top_check=True)


def test_missing_guard():
    prog = parse("""
        while
            print "hi"
        wend
    """)
    assert prog.diagnostics.has(diag.E_UNEXPECTED_ITEM)


def test_bad_guard():
    prog = parse("""
        do for 10
            print "hi"
        loop
    """)
    assert prog.diagnostics.has(diag.E_UNEXPECTED_ITEM)


def test_bad_nesting():
    prog = parse("""
        while 1
            do
                print "hi"
            wend
        loop
    """)
    assert prog.diagnostics.has(diag.E_UNEXPECTED_ITEM)
