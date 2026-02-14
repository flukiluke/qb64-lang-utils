from ..ast import Call, Print, Var
from .helpers import Ast, parse_clean


def test_musthave():
    prog = parse_clean("""
        $syntax:musthave=$
        declare function foo$
        print foo$; foo;
    """)
    assert prog.main.find(Print).args == [Ast(Call), Ast(Var)]
