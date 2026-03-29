from .. import diagnostics as diag
from .. import parse
from ..ast import Call, Constant, EmptyExpr, If, Print, Var
from .helpers import Ast, builtin_proc, parse_clean


def test_strictsigil_string():
    prog = parse_clean("""
        $flags:strictsigil=on
        declare function foo$
        print foo$; foo
    """)
    assert prog.main.find(Print).args == [Ast(Call), Print.Element.SEMICOLON, Ast(Var)]


def test_strictsigil_num():
    prog = parse_clean("""
        $flags:strictsigil=on
        declare function foo%
        print foo; foo$
    """)
    assert prog.main.find(Print).args == [Ast(Call), Print.Element.SEMICOLON, Ast(Var)]


def test_strictsigil_num_bad():
    assert parse("""
        $flags:strictsigil=on
        declare function foo%
        print foo%;
    """).diagnostics.has(diag.E_EXISTING_DEF_SIGIL_CLASH)


def test_strictsigil_num_bad_sigil():
    assert parse("""
        $flags:strictsigil=on
        declare function foo%
        print foo&;
    """).diagnostics.has(diag.E_EXISTING_DEF_SIGIL_CLASH)


def test_strictsigil_combination():
    prog = parse_clean("""
        $flags:overload=on,strictsigil=on
        declare function foo$
        declare sub foo
        if 1 then foo
        print foo$
    """)
    assert prog.main.find(If).true_branch == [Ast(Call)]


def test_end_command():
    # Not custom syntax, but special enough to need a dedicated test
    # because of the conflict with the syntactic structure.
    prog = parse_clean("end \n end 1")
    assert list(prog.main.find_all(Call)) == [
        Ast(Call, builtin_proc("end")),
        Ast(Call, builtin_proc("end"), [Ast(Constant, 1)]),
    ]


def test_circle():
    assert parse_clean("circle (1.0, 2.0), 3.0").main.find(Call) == Ast(
        Call,
        args=[
            Ast(EmptyExpr),
            Ast(Constant, 1.0),
            Ast(Constant, 2.0),
            Ast(Constant, 3.0),
            Ast(EmptyExpr),
            Ast(EmptyExpr),
            Ast(EmptyExpr),
            Ast(EmptyExpr),
        ],
    )
    assert parse_clean("circle step(1.0, 2.0), 3.0").main.find(Call) == Ast(
        Call,
        args=[
            Ast(Constant, -1),
            Ast(Constant, 1.0),
            Ast(Constant, 2.0),
            Ast(Constant, 3.0),
            Ast(EmptyExpr),
            Ast(EmptyExpr),
            Ast(EmptyExpr),
            Ast(EmptyExpr),
        ],
    )
    assert parse_clean("circle (1.0, 2.0), 3.0, &hffffffff~&").main.find(Call) == Ast(
        Call,
        args=[
            Ast(EmptyExpr),
            Ast(Constant, 1.0),
            Ast(Constant, 2.0),
            Ast(Constant, 3.0),
            Ast(Constant, 0xFFFFFFFF),
            Ast(EmptyExpr),
            Ast(EmptyExpr),
            Ast(EmptyExpr),
        ],
    )
    assert parse_clean("circle (1.0, 2.0), 3.0, , 4.0, 5.0").main.find(Call) == Ast(
        Call,
        args=[
            Ast(EmptyExpr),
            Ast(Constant, 1.0),
            Ast(Constant, 2.0),
            Ast(Constant, 3.0),
            Ast(EmptyExpr),
            Ast(Constant, 4.0),
            Ast(Constant, 5.0),
            Ast(EmptyExpr),
        ],
    )
    assert parse_clean("circle (1.0, 2.0), 3.0, , 4.0, 5.0, 6.0").main.find(
        Call
    ) == Ast(
        Call,
        args=[
            Ast(EmptyExpr),
            Ast(Constant, 1.0),
            Ast(Constant, 2.0),
            Ast(Constant, 3.0),
            Ast(EmptyExpr),
            Ast(Constant, 4.0),
            Ast(Constant, 5.0),
            Ast(Constant, 6.0),
        ],
    )
    assert parse_clean("circle (1.0, 2.0), 3.0, , , , 6.0").main.find(Call) == Ast(
        Call,
        args=[
            Ast(EmptyExpr),
            Ast(Constant, 1.0),
            Ast(Constant, 2.0),
            Ast(Constant, 3.0),
            Ast(EmptyExpr),
            Ast(EmptyExpr),
            Ast(EmptyExpr),
            Ast(Constant, 6.0),
        ],
    )


def test_eof():
    assert parse_clean("x = eof(3&)").main.find(Call) == Ast(
        Call, args=[Ast(Constant, 3)]
    )
    assert parse_clean("x = eof(#x&)").main.find(Call) == Ast(Call, args=[Ast(Var)])
