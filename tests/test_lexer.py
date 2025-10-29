from dataclasses import dataclass
from typing import Any

import lexer
from ast_nodes import Procedure
from datatypes import BUILTIN_TYPES, TypeSignature
from symbols import SymbolStore

SINGLE = BUILTIN_TYPES["single"]


@dataclass
class Token:
    type: str
    value: Any = None
    lineno: int | None = None


def check(
    text: str, expecteds: Token | list[Token], symbols: SymbolStore | None = None
):
    lex = lexer.Lexer(symbols if symbols else SymbolStore())
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
    check("? " + text, [Token("KEYWORD", "?"), expected])


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


def test_keyword():
    check("?", Token("KEYWORD", "?"))
    check("if", Token("KEYWORD", "if"))
    check("if%", Token("ERROR"))
    check("if$", Token("ID", ("if", BUILTIN_TYPES["string"])))


def test_procedure():
    symbols = SymbolStore()
    a_sub = Procedure("a_sub", TypeSignature(BUILTIN_TYPES["_none"], []))
    a_function = Procedure("a_function", TypeSignature(BUILTIN_TYPES["string"], []))
    symbols.procedures["a_sub"] = a_sub
    symbols.procedures["a_function"] = a_function

    check("a_sub", Token("PROCEDURE", a_sub), symbols)
    check("a_sub!", Token("ERROR"), symbols)
    check("a_function", Token("PROCEDURE", a_function), symbols)
    check("a_function$", Token("PROCEDURE", a_function), symbols)
    check("a_function!", Token("ERROR"), symbols)


def test_id():
    check("Foo", Token("ID", ("foo", SINGLE)))
    check("Foo_bar", Token("ID", ("foo_bar", SINGLE)))
    check("_foo", Token("ID", ("_foo", SINGLE)))
    check("foo23x", Token("ID", ("foo23x", SINGLE)))
    check("foo.bar", Token("ID", ("foo.bar", SINGLE)))


def test_id_builtin_sigil():
    check("foo`", Token("ID", ("foo", BUILTIN_TYPES["_bit"])))
    check("foo%%", Token("ID", ("foo", BUILTIN_TYPES["_byte"])))
    check("foo%", Token("ID", ("foo", BUILTIN_TYPES["integer"])))
    check("foo&", Token("ID", ("foo", BUILTIN_TYPES["long"])))
    check("foo&&", Token("ID", ("foo", BUILTIN_TYPES["_integer64"])))
    check("foo%&", Token("ID", ("foo", BUILTIN_TYPES["_offset"])))
    check("foo~`", Token("ID", ("foo", BUILTIN_TYPES["_unsigned _bit"])))
    check("foo~%%", Token("ID", ("foo", BUILTIN_TYPES["_unsigned _byte"])))
    check("foo~%", Token("ID", ("foo", BUILTIN_TYPES["_unsigned integer"])))
    check("foo~&", Token("ID", ("foo", BUILTIN_TYPES["_unsigned long"])))
    check("foo~&&", Token("ID", ("foo", BUILTIN_TYPES["_unsigned _integer64"])))
    check("foo~%&", Token("ID", ("foo", BUILTIN_TYPES["_unsigned _offset"])))
    check("foo!", Token("ID", ("foo", BUILTIN_TYPES["single"])))
    check("foo#", Token("ID", ("foo", BUILTIN_TYPES["double"])))
    check("foo##", Token("ID", ("foo", BUILTIN_TYPES["_float"])))
    check("foo$", Token("ID", ("foo", BUILTIN_TYPES["string"])))


def test_id_custom_sigil():
    def check_custom_sigil(input: str, type_name: str):
        symbols = SymbolStore()
        lex = lexer.Lexer(symbols)
        lex.input(input)
        result = list(lex)[0]
        assert result.type == "ID"
        assert result.value == ("foo", symbols.types[type_name])

    check_custom_sigil("foo`10", "_bit * 10")
    check_custom_sigil("foo~`10", "_unsigned _bit * 10")
    check_custom_sigil("foo$10", "string * 10")


def test_check_punctuation():
    for s in [
        "<=",
        "<",
        ">=",
        ">",
        "<>",
        "=",
        "(",
        ")",
        "*",
        "/",
        "^",
        "\\",
        "+",
        "-",
        ";",
        ",",
        ".",
        "#",
    ]:
        check(s, Token("PUNCTUATION", s))


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
    check("foo: bar", [Token("LINE_LABEL", "foo"), Token("ID", ("bar", SINGLE))])
    check("foo.bar23:", Token("LINE_LABEL", "foo.bar23"))


def test_line_num():
    check("123", Token("LINE_NUM", "123"))
    check("123foo", [Token("LINE_NUM", "123"), Token("ID", ("foo", SINGLE))])
    check("123 foo", [Token("LINE_NUM", "123"), Token("ID", ("foo", SINGLE))])


def test_line_num_label():
    check("123 foo:", Token("LINE_NUM_LABEL", ("123", "foo")))
    check(
        "123foo:bar",
        [Token("LINE_NUM_LABEL", ("123", "foo")), Token("ID", ("bar", SINGLE))],
    )


def test_line_split():
    check(
        "print foo:bar",
        [Token("KEYWORD"), Token("ID"), Token("LINE_SPLIT"), Token("ID")],
    )
    check("print foo:", [Token("KEYWORD"), Token("ID"), Token("LINE_SPLIT")])
    check(":foo", [Token("LINE_SPLIT"), Token("ID")])


def test_line_join():
    check(
        "foo_\nbar", [Token("ID", ("foo", SINGLE), 1), Token("ID", ("bar", SINGLE), 2)]
    )
    check(
        "foo_ \nbar", [Token("ID", ("foo", SINGLE), 1), Token("ID", ("bar", SINGLE), 2)]
    )
    check("foo_\n", Token("ID", ("foo", SINGLE), 1))
    check("_\n", [])
    check(
        "foo_\nbar_\nbaz",
        [
            Token("ID", ("foo", SINGLE), 1),
            Token("ID", ("bar", SINGLE), 2),
            Token("ID", ("baz", SINGLE), 3),
        ],
    )
