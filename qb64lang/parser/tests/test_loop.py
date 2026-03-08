from .. import diagnostics as diag
from .. import parse
from ..ast import Call, Constant, Loop, Print
from .helpers import Ast, builtin_proc, parse_clean


def test_do_while():
    loop = parse_clean(
        """
        do while x > 1
            print "hi"
        loop"""
    ).main.find(Loop)
    assert loop == Ast(Loop, Ast(Call, builtin_proc(">")), [Ast(Print)], None)


def test_do_until():
    loop = parse_clean(
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
        None,
    )


def test_loop_while():
    loop = parse_clean(
        """
        do
            print "hi"
        loop while x > 1
    """
    ).main.find(Loop)
    assert loop == Ast(Loop, None, [Ast(Print)], Ast(Call, builtin_proc(">")))


def test_loop_until():
    loop = parse_clean(
        """
        do
            print "hi"
        loop until x > 1
    """
    ).main.find(Loop)
    assert loop == Ast(
        Loop,
        None,
        [Ast(Print)],
        Ast(Call, builtin_proc("<>"), [Ast(Call, builtin_proc(">")), Ast(Constant, 0)]),
    )


def test_infinite_loop():
    loop = parse_clean(
        """
        do
        print "hi"
        loop
        """
    ).main.find(Loop)
    assert loop == Ast(Loop, None, [Ast(Print)], None)


def test_while():
    loop = parse_clean(
        """
        while x > 1
            print "hi"
        wend
    """
    ).main.find(Loop)
    assert loop == Ast(Loop, Ast(Call, builtin_proc(">")), [Ast(Print)], None)


def test_empty_loop():
    loop = parse_clean("while x > 1:wend").main.find(Loop)
    assert loop == Ast(Loop, Ast(Call, builtin_proc(">")), [], None)


def test_nested_loop():
    loop = parse_clean(
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
        [Ast(Loop, None, [Ast(Print)], Ast(Call, builtin_proc("<")))],
        None,
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
    assert prog.main.find(Loop) == Ast(Loop, Ast(Call), [Ast(Print)], Ast(Call))


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


def test_missing_newline_while():
    prog = parse("while x > 1 ? 2 : wend")
    assert prog.diagnostics.has(diag.E_UNEXPECTED_ITEM)

    prog = parse("while x > 1 : wend ? 2")
    assert prog.diagnostics.has(diag.E_UNEXPECTED_ITEM)


def test_missing_newline_do():
    prog = parse("""do while x > 1 ? 2 : loop""")
    assert prog.diagnostics.has(diag.E_UNEXPECTED_ITEM)

    prog = parse("do ? 2 : loop")
    assert prog.diagnostics.has(diag.E_UNEXPECTED_ITEM)

    prog = parse("do\nloop ? 4")
    assert prog.diagnostics.has(diag.E_UNEXPECTED_ITEM)
