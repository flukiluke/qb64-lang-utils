from dataclasses import dataclass
from typing import Any

import lexer


@dataclass
class Token:
    type: str
    value: Any = None
    lineno: int | None = None


def check(text: str, expecteds: Token | list[Token]):
    lex = lexer.Lexer()
    lex.input(text)
    actuals = list(lex)
    if isinstance(expecteds, Token):
        expecteds = [expecteds]
    assert len(actuals) == len(expecteds)
    for actual, expected in zip(actuals, expecteds):
        assert actual.type == expected.type
        if expected.value is not None:
            assert actual.value == expected.value
        if expected.lineno is not None:
            assert actual.lineno == expected.lineno


def check_expr(text: str, expected: Token):
    check("? " + text, [Token("ID"), expected])


def test_int_lit():
    check_expr("1", Token("INT_LIT", 1))
    check_expr("1234567890", Token("INT_LIT", 1234567890))
    check_expr("034", Token("INT_LIT", 34))


def test_dec_lit():
    check_expr("1.25", Token("DEC_LIT", 1.25))
    check_expr(".25", Token("DEC_LIT", 0.25))
    check_expr("23.", Token("DEC_LIT", 23.0))


def test_base_lit():
    check_expr("&H123456789ABCDEF0", Token("BASE_LIT", 0x123456789ABCDEF0))
    check_expr("&h08", Token("BASE_LIT", 0x8))
    check_expr("&B10", Token("BASE_LIT", 0b10))
    check_expr("&b001", Token("BASE_LIT", 0b1))
    check_expr("&O12345670", Token("BASE_LIT", 0o12345670))
    check_expr("&o002", Token("BASE_LIT", 0o2))


def test_exp_lit():
    for c in "d", "e", "f", "D", "E", "F":
        check_expr(f"17{c}2", Token("EXP_LIT", 1700))
        check_expr(f"17.25{c}2", Token("EXP_LIT", 1725))
        check_expr(f"1.725{c}+2", Token("EXP_LIT", 172.5))
        check_expr(f".1725{c}2", Token("EXP_LIT", 17.25))
        check_expr(f".1725{c}10", Token("EXP_LIT", 0.1725e10))
        check_expr(f"17{c}", Token("EXP_LIT", 17))
        check_expr(f"17.25{c}", Token("EXP_LIT", 17.25))
        check_expr(f".25{c}", Token("EXP_LIT", 0.25))
        check_expr(f".25{c}", Token("EXP_LIT", 0.25))
        check_expr(f"25{c}-2", Token("EXP_LIT", 0.25))
        check_expr(f"2.5{c}-10", Token("EXP_LIT", 2.5e-10))


def test_string_lit():
    check_expr(r'"hello"', Token("STRING_LIT", r"hello"))


def test_id():
    check("?", Token("ID", ("Print", None)))
    check("Foo", Token("ID", ("Foo", None)))
    check("Foo_bar", Token("ID", ("Foo_bar", None)))
    check("_foo", Token("ID", ("_foo", None)))
    check("foo23x", Token("ID", ("foo23x", None)))
    check("foo.bar", Token("ID", ("foo.bar", None)))


def test_id_sigil():
    check("foo`", Token("ID", ("foo", "`")))
    check("foo`10", Token("ID", ("foo", "`10")))
    check("foo%%", Token("ID", ("foo", "%%")))
    check("foo%", Token("ID", ("foo", "%")))
    check("foo&", Token("ID", ("foo", "&")))
    check("foo&&", Token("ID", ("foo", "&&")))
    check("foo%&", Token("ID", ("foo", "%&")))
    check("foo~`", Token("ID", ("foo", "~`")))
    check("foo~`5", Token("ID", ("foo", "~`5")))
    check("foo~%%", Token("ID", ("foo", "~%%")))
    check("foo~%", Token("ID", ("foo", "~%")))
    check("foo~&", Token("ID", ("foo", "~&")))
    check("foo~&&", Token("ID", ("foo", "~&&")))
    check("foo~%&", Token("ID", ("foo", "~%&")))
    check("foo$", Token("ID", ("foo", "$")))
    check("foo$10", Token("ID", ("foo", "$10")))


def test_check_punctuation():
    check("<=", Token("LT_EQ"))
    check("<", Token("LT"))
    check(">=", Token("GT_EQ"))
    check(">", Token("GT"))
    check("<>", Token("NEQ"))
    check("=", Token("EQUALS"))
    check("(", Token("OPAREN"))
    check(")", Token("CPAREN"))
    check("*", Token("STAR"))
    check("/", Token("SLASH"))
    check("^", Token("CARET"))
    check("\\", Token("BACKSLASH"))
    check("+", Token("PLUS"))
    check("-", Token("DASH"))
    check(";", Token("SEMICOLON"))
    check(",", Token("COMMA"))
    check(".", Token("DOT"))
    check("#", Token("HASH"))


def test_comment():
    check("'foo", Token("COMMENT", "foo"))
    check("this ' comment", [Token("ID"), Token("COMMENT", " comment")])
    check("that '", [Token("ID"), Token("COMMENT", "")])


def test_remark():
    check("rem foo", Token("REMARK", " foo"))
    check("foo REM", [Token("ID"), Token("REMARK", "")])


def test_line_label():
    check("foo:", Token("LINE_LABEL", "foo"))
    check("foo :", Token("LINE_LABEL", "foo"))
    check("foo: bar", [Token("LINE_LABEL", "foo"), Token("ID", ("bar", None))])
    check("foo.bar23:", Token("LINE_LABEL", "foo.bar23"))


def test_line_num():
    check("123", Token("LINE_NUM", "123"))
    check("123foo", [Token("LINE_NUM", "123"), Token("ID", ("foo", None))])
    check("123 foo", [Token("LINE_NUM", "123"), Token("ID", ("foo", None))])


def test_line_num_label():
    check("123 foo:", Token("LINE_NUM_LABEL", ("123", "foo")))
    check(
        "123foo:bar",
        [Token("LINE_NUM_LABEL", ("123", "foo")), Token("ID", ("bar", None))],
    )


def test_line_split():
    check("print foo:bar", [Token("ID"), Token("ID"), Token("LINE_SPLIT"), Token("ID")])
    check("print foo:", [Token("ID"), Token("ID"), Token("LINE_SPLIT")])
    check(":foo", [Token("LINE_SPLIT"), Token("ID")])


def test_line_join():
    check("foo_\nbar", [Token("ID", ("foo", None), 1), Token("ID", ("bar", None), 2)])
    check("foo_ \nbar", [Token("ID", ("foo", None), 1), Token("ID", ("bar", None), 2)])
    check("foo_\n", Token("ID", ("foo", None), 1))
    check("_\n", [])
    check(
        "foo_\nbar_\nbaz",
        [
            Token("ID", ("foo", None), 1),
            Token("ID", ("bar", None), 2),
            Token("ID", ("baz", None), 3),
        ],
    )
