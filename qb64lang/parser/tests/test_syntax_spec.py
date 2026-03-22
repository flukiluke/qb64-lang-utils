from .. import diagnostics as diag
from .. import parse
from ..ast import Call, Cast, Constant, EmptyExpr
from ..datatypes import TYPE_INTEGER, TYPE_LONG
from ..ply import LexToken
from ..syntax import (
    AlternateItem,
    ExprItem,
    LiteralItem,
    OptionalItem,
    SyntaxSpec,
    compile_syntax_spec,
)
from .helpers import Ast, parse_clean


def spec_clean(s: str):
    diags = diag.DiagnosticStore()
    # Supply a token so the error handling doesn't barf
    tok = LexToken()
    tok.type = "TEST"
    tok.value = "test"
    tok.lexpos = 0
    tok.lexend = 10
    spec = compile_syntax_spec(s, diags, tok)
    return spec


def test_spec_expr_punctuation():
    assert spec_clean("foo") == SyntaxSpec([ExprItem("foo")], ["foo"])
    assert spec_clean("a,#b - (c,d)") == SyntaxSpec(
        [
            ExprItem("a"),
            LiteralItem(","),
            LiteralItem("#"),
            ExprItem("b"),
            LiteralItem("-"),
            LiteralItem("("),
            ExprItem("c"),
            LiteralItem(","),
            ExprItem("d"),
            LiteralItem(")"),
        ],
        ["a", "b", "c", "d"],
    )


def test_spec_alternation():
    assert spec_clean("{FOO bar baz}") == SyntaxSpec(
        [
            AlternateItem(
                [
                    "foo",
                    "bar",
                    "baz",
                ]
            )
        ],
        [],
    )
    assert spec_clean("A1:{foo bar}") == SyntaxSpec(
        [
            AlternateItem(
                [
                    "foo",
                    "bar",
                ],
                "a1",
            )
        ],
        ["a1"],
    )


def test_spec_optional():
    assert spec_clean("[a]") == SyntaxSpec(
        [OptionalItem(SyntaxSpec([ExprItem("a")], ["a"]))], ["a"]
    )
    assert spec_clean("[[a][,[b]]]c") == SyntaxSpec(
        [
            OptionalItem(
                SyntaxSpec(
                    [
                        OptionalItem(SyntaxSpec([ExprItem("a")], ["a"])),
                        OptionalItem(
                            SyntaxSpec(
                                [
                                    LiteralItem(","),
                                    OptionalItem(SyntaxSpec([ExprItem("b")], ["b"])),
                                ],
                                ["b"],
                            )
                        ),
                    ],
                    ["a", "b"],
                )
            ),
            ExprItem("c"),
        ],
        ["a", "b", "c"],
    )


def test_spec_literals():
    assert spec_clean('s1:"step" "to"') == SyntaxSpec(
        [LiteralItem("step", "s1"), LiteralItem("to")], ["s1"]
    )


def test_expr():
    prog = parse_clean("$syntax:a,b,c\ndeclare sub s (a&,b%,c%) : s 3,4,5")
    assert prog.main.find(Call) == Ast(
        Call,
        args=[
            Ast(Cast, Ast(Constant, 3), TYPE_LONG),
            Ast(Constant, 4),
            Ast(Constant, 5),
        ],
    )


def test_missing_expr():
    assert parse("$syntax:a,b,c\ndeclare sub s(a%,b%,c%) : s 3,5").diagnostics.has(
        diag.E_UNEXPECTED_ITEM
    )


def test_literals():
    prog = parse_clean('$syntax:"foo" a:"bar"\ndeclare sub s(a%) : s foo bar')
    assert prog.main.find(Call) == Ast(
        Call,
        args=[
            Ast(Constant, -1),
        ],
    )


def test_missing_literal():
    assert parse('$syntax:"foo" a:"bar"\ndeclare sub s(a%) : s bar').diagnostics.has(
        diag.E_UNEXPECTED_ITEM
    )


def test_alternation():
    prog = parse_clean("""$syntax:a:{foo bar}
                       declare sub s(a%)
                       s foo
                       s bar""")
    assert list(prog.main.find_all(Call)) == [
        Ast(Call, args=[Ast(Constant, 1)]),
        Ast(Call, args=[Ast(Constant, 2)]),
    ]


def test_missing_alternation():
    assert parse("$syntax:a:{foo bar}\ndeclare sub s(a%) : s").diagnostics.has(
        diag.E_UNEXPECTED_ITEM
    )


def test_optional_expr():
    prog = parse_clean("""$syntax:[a]
                       declare sub s(a%)
                       s
                       s 2""")
    assert list(prog.main.find_all(Call)) == [
        Ast(Call, args=[Ast(EmptyExpr, TYPE_INTEGER)]),
        Ast(Call, args=[Ast(Constant, 2)]),
    ]


def test_many_optional_expr():
    prog = parse_clean("""$syntax:[a][,[b][,c]]
                        declare sub s(a%,b%,c%)
                        s
                        s 1
                        s , 2
                        s 1, , 3
                        s , , 3""")
    assert list(prog.main.find_all(Call)) == [
        Ast(
            Call,
            args=[
                Ast(EmptyExpr, TYPE_INTEGER),
                Ast(EmptyExpr, TYPE_INTEGER),
                Ast(EmptyExpr, TYPE_INTEGER),
            ],
        ),
        Ast(
            Call,
            args=[
                Ast(Constant, 1),
                Ast(EmptyExpr, TYPE_INTEGER),
                Ast(EmptyExpr, TYPE_INTEGER),
            ],
        ),
        Ast(
            Call,
            args=[
                Ast(EmptyExpr, TYPE_INTEGER),
                Ast(Constant, 2),
                Ast(EmptyExpr, TYPE_INTEGER),
            ],
        ),
        Ast(
            Call,
            args=[Ast(Constant, 1), Ast(EmptyExpr, TYPE_INTEGER), Ast(Constant, 3)],
        ),
        Ast(
            Call,
            args=[
                Ast(EmptyExpr, TYPE_INTEGER),
                Ast(EmptyExpr, TYPE_INTEGER),
                Ast(Constant, 3),
            ],
        ),
    ]


def test_optional_alternation_literals():
    prog = parse_clean("""$syntax:[a:"foo"][,b:{bar baz}]
                       declare sub s(a%,b%)
                       s
                       s foo
                       s ,bar
                       s foo, bar""")
    assert list(prog.main.find_all(Call)) == [
        Ast(Call, args=[Ast(EmptyExpr, TYPE_INTEGER), Ast(EmptyExpr, TYPE_INTEGER)]),
        Ast(Call, args=[Ast(Constant, -1), Ast(EmptyExpr, TYPE_INTEGER)]),
        Ast(Call, args=[Ast(EmptyExpr, TYPE_INTEGER), Ast(Constant, 1)]),
        Ast(Call, args=[Ast(Constant, -1), Ast(Constant, 1)]),
    ]
