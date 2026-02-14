from .. import diagnostics as diag
from .. import parse
from ..ast import Call, If, Print, Var
from .helpers import Ast, parse_clean


def test_strictsigil_string():
    prog = parse_clean("""
        $syntax:strictsigil
        declare function foo$
        print foo$; foo;
    """)
    assert prog.main.find(Print).args == [Ast(Call), Ast(Var)]


def test_strictsigil_num():
    prog = parse_clean("""
        $syntax:strictsigil
        declare function foo%
        print foo; foo$;
    """)
    assert prog.main.find(Print).args == [Ast(Call), Ast(Var)]


def test_strictsigil_num_bad():
    assert parse("""
        $syntax:strictsigil
        declare function foo%
        print foo%;
    """).diagnostics.has(diag.E_EXISTING_DEF_SIGIL_CLASH)


def test_strictsigil_num_bad_sigil():
    assert parse("""
        $syntax:strictsigil
        declare function foo%
        print foo&;
    """).diagnostics.has(diag.E_EXISTING_DEF_SIGIL_CLASH)


def test_strictsigil_combination():
    prog = parse_clean("""
        $overload:on
        $syntax:strictsigil
        declare function foo$
        $syntax:strictsigil
        declare sub foo
        if 1 then foo
        print foo$
    """)
    assert prog.main.find(If).true_branch == [Ast(Call)]
