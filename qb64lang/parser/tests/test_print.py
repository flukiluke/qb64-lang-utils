from .. import diagnostics as diag
from .. import parse
from ..ast import Call, Constant, Print, Var
from .helpers import Ast, parse_clean


def test_empty():
    assert parse_clean("print").main.statements == [Ast(Print, [])]


def test_only_punctuation():
    assert parse_clean("print ;").main.statements == [
        Ast(Print, [Print.Element.SEMICOLON])
    ]
    assert parse_clean("print ,").main.statements == [Ast(Print, [Print.Element.COMMA])]
    assert parse_clean("print ,;,").main.statements == [
        Ast(
            Print,
            [
                Print.Element.COMMA,
                Print.Element.SEMICOLON,
                Print.Element.COMMA,
            ],
        )
    ]


def test_combined():
    assert parse_clean("print a").main.statements == [Ast(Print, [Ast(Var)])]
    assert parse_clean("print a; b + c, d").main.statements == [
        Ast(
            Print,
            [
                Ast(Var),
                Print.Element.SEMICOLON,
                Ast(Call),
                Print.Element.COMMA,
                Ast(Var),
            ],
        )
    ]


def test_auto_semicolon():
    assert parse_clean("print lcase$(x$) 100 b").main.statements == [
        Ast(
            Print,
            [
                Ast(Call),
                Print.Element.SEMICOLON,
                Ast(Constant),
                Print.Element.SEMICOLON,
                Ast(Var),
            ],
        )
    ]


def test_using():
    assert parse_clean('print using "###"; a').main.statements == [
        Ast(
            Print,
            [Print.Element.USING, Ast(Constant), Print.Element.SEMICOLON, Ast(Var)],
        )
    ]
    assert parse_clean('print using "#" + "#"; a').main.statements == [
        Ast(Print, [Print.Element.USING, Ast(Call), Print.Element.SEMICOLON, Ast(Var)])
    ]


def test_var_before_using():
    assert parse_clean('print x, using "#" + "#"; a').main.statements == [
        Ast(
            Print,
            [
                Ast(Var),
                Print.Element.COMMA,
                Print.Element.USING,
                Ast(Call),
                Print.Element.SEMICOLON,
                Ast(Var),
            ],
        )
    ]


def test_using_errors():
    assert parse("print using").diagnostics.has(diag.E_UNEXPECTED_ITEM)
    assert parse("print using f").diagnostics.has(diag.E_UNEXPECTED_ITEM)
    assert parse("print using f ,").diagnostics.has(diag.E_UNEXPECTED_ITEM)
    assert parse("print using f ;").diagnostics.has(diag.E_UNEXPECTED_ITEM)
    assert parse("print using f ; x ; using g ; y").diagnostics.has(diag.E_DUPE_USING)


def test_using_type():
    assert parse("print using 10; x$").diagnostics.has(diag.E_USING_NON_STRING)
