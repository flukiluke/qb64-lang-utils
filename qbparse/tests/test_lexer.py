from dataclasses import dataclass
from typing import Any

from qbparse.datatypes import (
    TYPE__BIT,
    TYPE__BYTE,
    TYPE__FLOAT,
    TYPE__INTEGER64,
    TYPE__NONE,
    TYPE__UNSIGNED__BIT,
    TYPE__UNSIGNED__BYTE,
    TYPE__UNSIGNED__INTEGER64,
    TYPE__UNSIGNED_INTEGER,
    TYPE__UNSIGNED_LONG,
    TYPE_DOUBLE,
    TYPE_INTEGER,
    TYPE_LONG,
    TYPE_SINGLE,
    TYPE_STRING,
    ExtendedFloat,
    TypeSignature,
)
from qbparse.lexer import Lexer
from qbparse.symbols import Procedure, SymbolStore


@dataclass
class Token:
    type: str
    value: Any = None
    lineno: int | None = None


def check(
    text: str, expecteds: Token | list[Token], symbols: SymbolStore | None = None
):
    lex = Lexer(symbols if symbols else SymbolStore())
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


def check_bitn(input: str, kind: str, value: int, sigil: str):
    symbols = SymbolStore()
    lex = Lexer(symbols)
    lex.input("? " + input)
    actuals = list(lex)
    assert len(actuals) == 2
    assert actuals[1].type == kind
    assert actuals[1].value == (value, symbols.lookup_sigil(sigil))


def test_int_lit_type_detection():
    check_expr("123", Token("NUM_LIT", (123, TYPE_INTEGER)))
    check_expr("32767", Token("NUM_LIT", (32767, TYPE_INTEGER)))
    check_expr("32768", Token("NUM_LIT", (32768, TYPE_LONG)))
    check_expr("2147483647", Token("NUM_LIT", (2147483647, TYPE_LONG)))
    check_expr("2147483648", Token("NUM_LIT", (2147483648, TYPE__INTEGER64)))
    check_expr(
        "9223372036854775807",
        Token("NUM_LIT", (9223372036854775807, TYPE__INTEGER64)),
    )
    check_expr(
        "9223372036854775808",
        Token("NUM_LIT", (9223372036854775808, TYPE__UNSIGNED__INTEGER64)),
    )
    check_expr(
        "18446744073709551615",
        Token("NUM_LIT", (18446744073709551615, TYPE__UNSIGNED__INTEGER64)),
    )
    check_expr("18446744073709551616", Token("ERROR"))


def test_int_lit_explicit_type():
    check_expr("0`", Token("NUM_LIT", (0, TYPE__BIT)))
    check_expr("1`", Token("ERROR"))
    check_expr("0~`", Token("NUM_LIT", (0, TYPE__UNSIGNED__BIT)))
    check_expr("1~`", Token("NUM_LIT", (1, TYPE__UNSIGNED__BIT)))
    check_expr("2~`", Token("ERROR"))
    check_expr("127%%", Token("NUM_LIT", (0x7F, TYPE__BYTE)))
    check_expr("128%%", Token("ERROR"))
    check_expr("128~%%", Token("NUM_LIT", (0x80, TYPE__UNSIGNED__BYTE)))
    check_expr("256~%%", Token("ERROR"))
    check_expr("32767%", Token("NUM_LIT", (0x7FFF, TYPE_INTEGER)))
    check_expr("32768%", Token("ERROR"))
    check_expr("32768~%", Token("NUM_LIT", (0x8000, TYPE__UNSIGNED_INTEGER)))
    check_expr("65535~%", Token("NUM_LIT", (0xFFFF, TYPE__UNSIGNED_INTEGER)))
    check_expr("65536%", Token("ERROR"))
    check_expr("2147483647&", Token("NUM_LIT", (0x7FFFFFFF, TYPE_LONG)))
    check_expr("2147483648&", Token("ERROR"))
    check_expr("2147483648~&", Token("NUM_LIT", (0x80000000, TYPE__UNSIGNED_LONG)))
    check_expr("4294967295~&", Token("NUM_LIT", (0xFFFFFFFF, TYPE__UNSIGNED_LONG)))
    check_expr("4294967296~&", Token("ERROR"))
    check_expr(
        "9223372036854775807&&",
        Token("NUM_LIT", (0x7FFFFFFFFFFFFFFF, TYPE__INTEGER64)),
    )
    check_expr("9223372036854775808&&", Token("ERROR"))
    check_expr(
        "9223372036854775808~&&",
        Token("NUM_LIT", (0x8000000000000000, TYPE__UNSIGNED__INTEGER64)),
    )
    check_expr(
        "18446744073709551615~&&",
        Token("NUM_LIT", (0xFFFFFFFFFFFFFFFF, TYPE__UNSIGNED__INTEGER64)),
    )
    check_expr("18446744073709551616~&&", Token("ERROR"))
    check_expr("1&&", Token("NUM_LIT", (1, TYPE__INTEGER64)))


def test_dec_lit():
    check_expr("1.25", Token("NUM_LIT", (1.25, TYPE_SINGLE)))
    check_expr(".25", Token("NUM_LIT", (0.25, TYPE_SINGLE)))
    check_expr("23.", Token("NUM_LIT", (23.0, TYPE_SINGLE)))


def test_dec_lit_type_detection():
    check_expr("1.234567", Token("NUM_LIT", (1.234567, TYPE_SINGLE)))
    check_expr("1.2345678", Token("NUM_LIT", (1.2345678, TYPE_DOUBLE)))
    check_expr("12345678.", Token("NUM_LIT", (12345678.0, TYPE_DOUBLE)))
    check_expr(
        ".1234567890123456",
        Token("NUM_LIT", (0.1234567890123456, TYPE_DOUBLE)),
    )
    check_expr(
        ".12345678901234567",
        Token("NUM_LIT", (ExtendedFloat(".12345678901234567"), TYPE__FLOAT)),
    )


def test_dec_lit_explicit_type():
    check_expr(
        "123456789012345678901234567890123456789.0!",
        Token("NUM_LIT", (1.2345678901234568e38, TYPE_SINGLE)),
    )
    check_expr(
        "123456789012345678901234567890123456789.0#",
        Token("NUM_LIT", (1.2345678901234568e38, TYPE_DOUBLE)),
    )
    check_expr("1234567890123456789012345678901234567890.0!", Token("ERROR"))
    check_expr(
        "1234567890123456789012345678901234567890.0#",
        Token("NUM_LIT", (1.2345678901234568e39, TYPE_DOUBLE)),
    )
    check_expr(
        "1234567890123456789012345678901234567890.0##",
        Token(
            "NUM_LIT",
            (
                ExtendedFloat("1.234567890123456789012345678901234567890", "39"),
                TYPE__FLOAT,
            ),
        ),
    )


def test_base_lit():
    check_expr(
        "&H123456789ABCDEF0",
        Token("NUM_LIT", (0x123456789ABCDEF0, TYPE__INTEGER64)),
    )
    check_expr("&h08", Token("NUM_LIT", (0x8, TYPE_INTEGER)))
    check_expr("&B10", Token("NUM_LIT", (0b10, TYPE_INTEGER)))
    check_expr("&b001", Token("NUM_LIT", (0b1, TYPE_INTEGER)))
    check_expr("&O12345670", Token("NUM_LIT", (0o12345670, TYPE_LONG)))
    check_expr("&o002", Token("NUM_LIT", (0o2, TYPE_INTEGER)))


def test_base_lit_type_detection():
    check_expr("&h0", Token("NUM_LIT", (0, TYPE_INTEGER)))
    check_expr("&h7fff", Token("NUM_LIT", (0x7FFF, TYPE_INTEGER)))
    # This behaviour is whacky, probably deserves a warning
    check_expr("&h8000", Token("NUM_LIT", (-0x8000, TYPE_INTEGER)))
    check_expr("&hDEAD", Token("NUM_LIT", (-8531, TYPE_INTEGER)))
    check_expr("&h7fffffff", Token("NUM_LIT", (0x7FFFFFFF, TYPE_LONG)))
    check_expr("&h80000000", Token("NUM_LIT", (-0x80000000, TYPE_LONG)))
    check_expr(
        "&h7fffffffffffffff",
        Token("NUM_LIT", (0x7FFFFFFFFFFFFFFF, TYPE__INTEGER64)),
    )
    check_expr(
        "&h8000000000000000",
        Token("NUM_LIT", (-0x8000000000000000, TYPE__INTEGER64)),
    )
    check_expr(
        "&hffffffffffffffff",
        Token("NUM_LIT", (-1, TYPE__INTEGER64)),
    )
    check_expr("&h10000000000000000", Token("ERROR"))


def test_base_lit_explicit_bitn():
    check_bitn("&b1`1", "NUM_LIT", -1, "`1")
    check_expr("&b10`1", Token("ERROR"))
    check_bitn("&b1`4", "NUM_LIT", 1, "`4")
    check_bitn("&b1010`4", "NUM_LIT", -6, "`4")
    check_bitn("&b1~`1", "NUM_LIT", 1, "~`1")
    check_expr("&b10~`1", Token("ERROR"))
    check_bitn("&b1010~`4", "NUM_LIT", 10, "~`4")


def test_base_lit_explicit_type():
    check_expr("&b0`", Token("NUM_LIT", (0, TYPE__BIT)))
    check_expr("&b1`", Token("NUM_LIT", (-1, TYPE__BIT)))
    check_expr("&b10`", Token("ERROR"))
    check_expr("&o0~`", Token("NUM_LIT", (0, TYPE__UNSIGNED__BIT)))
    check_expr("&o1~`", Token("NUM_LIT", (1, TYPE__UNSIGNED__BIT)))
    check_expr("&o2~`", Token("ERROR"))
    check_expr("&h7f%%", Token("NUM_LIT", (0x7F, TYPE__BYTE)))
    check_expr("&h80%%", Token("NUM_LIT", (-0x80, TYPE__BYTE)))
    check_expr("&h80~%%", Token("NUM_LIT", (0x80, TYPE__UNSIGNED__BYTE)))
    check_expr("&h100~%%", Token("ERROR"))
    check_expr("&h7fff%", Token("NUM_LIT", (0x7FFF, TYPE_INTEGER)))
    check_expr("&h8000%", Token("NUM_LIT", (-0x8000, TYPE_INTEGER)))
    check_expr("&h8000~%", Token("NUM_LIT", (0x8000, TYPE__UNSIGNED_INTEGER)))
    check_expr("&hffff~%", Token("NUM_LIT", (0xFFFF, TYPE__UNSIGNED_INTEGER)))
    check_expr("&h10000%", Token("ERROR"))
    check_expr("&h7fffffff&", Token("NUM_LIT", (0x7FFFFFFF, TYPE_LONG)))
    check_expr("&h80000000&", Token("NUM_LIT", (-0x80000000, TYPE_LONG)))
    check_expr("&h80000000~&", Token("NUM_LIT", (0x80000000, TYPE__UNSIGNED_LONG)))
    check_expr("&hffffffff~&", Token("NUM_LIT", (0xFFFFFFFF, TYPE__UNSIGNED_LONG)))
    check_expr("&h100000000~&", Token("ERROR"))
    check_expr(
        "&h7fffffffffffffff&&",
        Token("NUM_LIT", (0x7FFFFFFFFFFFFFFF, TYPE__INTEGER64)),
    )
    check_expr(
        "&h8000000000000000&&",
        Token("NUM_LIT", (-0x8000000000000000, TYPE__INTEGER64)),
    )
    check_expr(
        "&h8000000000000000~&&",
        Token("NUM_LIT", (0x8000000000000000, TYPE__UNSIGNED__INTEGER64)),
    )
    check_expr(
        "&hffffffffffffffff~&&",
        Token("NUM_LIT", (0xFFFFFFFFFFFFFFFF, TYPE__UNSIGNED__INTEGER64)),
    )
    check_expr("&h10000000000000000~&&", Token("ERROR"))
    check_expr("&b1&&", Token("NUM_LIT", (1, TYPE__INTEGER64)))


def test_exp_e_lit():
    expected_type = TYPE_SINGLE
    for c in "e", "E":
        check_expr(f"17{c}2", Token("NUM_LIT", (1700, expected_type)))
        check_expr(f"17.25{c}2", Token("NUM_LIT", (1725, expected_type)))
        check_expr(f"1.725{c}+2", Token("NUM_LIT", (172.5, expected_type)))
        check_expr(f".1725{c}2", Token("NUM_LIT", (17.25, expected_type)))
        check_expr(f".1725{c}10", Token("NUM_LIT", (0.1725e10, expected_type)))
        check_expr(f"17{c}", Token("NUM_LIT", (17, expected_type)))
        check_expr(f"17.25{c}", Token("NUM_LIT", (17.25, expected_type)))
        check_expr(f".25{c}", Token("NUM_LIT", (0.25, expected_type)))
        check_expr(f"25.{c}", Token("NUM_LIT", (25, expected_type)))
        check_expr(f"25{c}-2", Token("NUM_LIT", (0.25, expected_type)))
        check_expr(f"2.5{c}-10", Token("NUM_LIT", (2.5e-10, expected_type)))
    check_expr("3e39", Token("ERROR"))


def test_exp_d_lit():
    expected_type = TYPE_DOUBLE
    for c in "d", "D":
        check_expr(f"17{c}2", Token("NUM_LIT", (1700, expected_type)))
        check_expr(f"17.25{c}2", Token("NUM_LIT", (1725, expected_type)))
        check_expr(f"1.725{c}+2", Token("NUM_LIT", (172.5, expected_type)))
        check_expr(f".1725{c}2", Token("NUM_LIT", (17.25, expected_type)))
        check_expr(f".1725{c}10", Token("NUM_LIT", (0.1725e10, expected_type)))
        check_expr(f"17{c}", Token("NUM_LIT", (17, expected_type)))
        check_expr(f"17.25{c}", Token("NUM_LIT", (17.25, expected_type)))
        check_expr(f".25{c}", Token("NUM_LIT", (0.25, expected_type)))
        check_expr(f"25.{c}", Token("NUM_LIT", (25, expected_type)))
        check_expr(f"25{c}-2", Token("NUM_LIT", (0.25, expected_type)))
        check_expr(f"2.5{c}-10", Token("NUM_LIT", (2.5e-10, expected_type)))
    check_expr("1.8d308", Token("ERROR"))


def test_exp_f_lit():
    expected_type = TYPE__FLOAT
    for c in "f", "F":
        check_expr(f"17{c}2", Token("NUM_LIT", (ExtendedFloat("1700"), expected_type)))
        check_expr(
            f"17.25{c}2", Token("NUM_LIT", (ExtendedFloat("1725"), expected_type))
        )
        check_expr(
            f"1.725{c}+2", Token("NUM_LIT", (ExtendedFloat("172.5"), expected_type))
        )
        check_expr(
            f".1725{c}2", Token("NUM_LIT", (ExtendedFloat("17.25"), expected_type))
        )
        check_expr(
            f".1725{c}10",
            Token("NUM_LIT", (ExtendedFloat("1.725", "9"), expected_type)),
        )
        check_expr(f"17{c}", Token("NUM_LIT", (ExtendedFloat("17"), expected_type)))
        check_expr(
            f"17.25{c}", Token("NUM_LIT", (ExtendedFloat("17.25"), expected_type))
        )
        check_expr(f".25{c}", Token("NUM_LIT", (ExtendedFloat(".25"), expected_type)))
        check_expr(f"25.{c}", Token("NUM_LIT", (ExtendedFloat("25"), expected_type)))
        check_expr(
            f"25{c}-2", Token("NUM_LIT", (ExtendedFloat("2.5", "-1"), expected_type))
        )
        check_expr(
            f"2.5{c}-10", Token("NUM_LIT", (ExtendedFloat("2.5", "-10"), expected_type))
        )
    check_expr("1.2f4932", Token("ERROR"))


def test_string_lit():
    check_expr(r'"hello"', Token("STRING_LIT", r"hello"))


def test_keyword():
    check("?", Token("KEYWORD", "?"))
    check("if", Token("KEYWORD", "if"))
    check("if%", Token("ERROR"))
    check("if$", Token("ID", ("if", TYPE_STRING)))


def test_procedure():
    symbols = SymbolStore()
    a_sub = Procedure("a_sub", TypeSignature(TYPE__NONE, []))
    a_function = Procedure("a_function", TypeSignature(TYPE_STRING, []))
    a_string_builtin = Procedure("a_string_builtin$", TypeSignature(TYPE_STRING, []))
    symbols.procedures["a_sub"] = a_sub
    symbols.procedures["a_function"] = a_function
    symbols.procedures["a_string_builtin$"] = a_string_builtin

    check("a_sub", Token("PROCEDURE", a_sub), symbols)
    check("a_sub!", Token("ERROR"), symbols)
    check("a_function", Token("PROCEDURE", a_function), symbols)
    check("a_function$", Token("PROCEDURE", a_function), symbols)
    check("a_function!", Token("ERROR"), symbols)
    check("a_string_builtin", Token("ID", ("a_string_builtin", TYPE_SINGLE)), symbols)
    check("a_string_builtin$", Token("PROCEDURE", a_string_builtin), symbols)


def test_id():
    check("Foo", Token("ID", ("foo", TYPE_SINGLE)))
    check("Foo_bar", Token("ID", ("foo_bar", TYPE_SINGLE)))
    check("_foo", Token("ID", ("_foo", TYPE_SINGLE)))
    check("foo23x", Token("ID", ("foo23x", TYPE_SINGLE)))
    check("foo.bar", Token("ID", ("foo.bar", TYPE_SINGLE)))


def test_id_builtin_sigil():
    check("foo`", Token("ID", ("foo", TYPE__BIT)))
    check("foo%%", Token("ID", ("foo", TYPE__BYTE)))
    check("foo%", Token("ID", ("foo", TYPE_INTEGER)))
    check("foo&", Token("ID", ("foo", TYPE_LONG)))
    check("foo&&", Token("ID", ("foo", TYPE__INTEGER64)))
    # check("foo%&", Token("ID", ("foo", BUILTIN_TYPES["_offset"])))
    check("foo~`", Token("ID", ("foo", TYPE__UNSIGNED__BIT)))
    check("foo~%%", Token("ID", ("foo", TYPE__UNSIGNED__BYTE)))
    check("foo~%", Token("ID", ("foo", TYPE__UNSIGNED_INTEGER)))
    check("foo~&", Token("ID", ("foo", TYPE__UNSIGNED_LONG)))
    check("foo~&&", Token("ID", ("foo", TYPE__UNSIGNED__INTEGER64)))
    # check("foo~%&", Token("ID", ("foo", BUILTIN_TYPES["_unsigned _offset"])))
    check("foo!", Token("ID", ("foo", TYPE_SINGLE)))
    check("foo#", Token("ID", ("foo", TYPE_DOUBLE)))
    check("foo##", Token("ID", ("foo", TYPE__FLOAT)))
    check("foo$", Token("ID", ("foo", TYPE_STRING)))


def test_id_custom_sigil():
    def check_custom_sigil(input: str, type_name: str):
        symbols = SymbolStore()
        lex = Lexer(symbols)
        lex.input(input)
        result = list(lex)[0]
        assert result.type == "ID"
        assert result.value == ("foo", symbols.types[type_name])

    check_custom_sigil("foo`10", "_bit * 10")
    check_custom_sigil("foo~`10", "_unsigned _bit * 10")
    check_custom_sigil("foo$10", "string * 10")
    check_expr("foo$0", Token("ERROR"))
    check_expr("foo`65", Token("ERROR"))
    check_expr("foo~`65", Token("ERROR"))


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
    check("'foo", Token("NEWLINE", "'"))
    check("this ' comment", [Token("ID"), Token("NEWLINE", "'")])
    check("that '", [Token("ID"), Token("NEWLINE", "'")])
    check("'foo\n", Token("NEWLINE", "'"))
    check("this ' comment\n", [Token("ID"), Token("NEWLINE", "'")])
    check("that '\n  ", [Token("ID"), Token("NEWLINE", "'")])


def test_remark():
    check("rem foo", Token("NEWLINE", "rem"))
    check("foo REM", [Token("ID"), Token("NEWLINE", "rem")])
    check("rem foo\n", Token("NEWLINE", "rem"))
    check("foo REM\n  ", [Token("ID"), Token("NEWLINE", "rem")])


def test_line_label():
    check("foo:", Token("LINE_LABEL", "foo"))
    check("foo :", Token("LINE_LABEL", "foo"))
    check("foo: bar", [Token("LINE_LABEL", "foo"), Token("ID", ("bar", TYPE_SINGLE))])
    check("foo.bar23:", Token("LINE_LABEL", "foo.bar23"))


def test_line_num():
    check("123", Token("LINE_NUM", "123"))
    check("123foo", [Token("LINE_NUM", "123"), Token("ID", ("foo", TYPE_SINGLE))])
    check("123 foo", [Token("LINE_NUM", "123"), Token("ID", ("foo", TYPE_SINGLE))])


def test_line_num_label():
    check("123 foo:", Token("LINE_NUM_LABEL", ("123", "foo")))
    check(
        "123foo:bar",
        [Token("LINE_NUM_LABEL", ("123", "foo")), Token("ID", ("bar", TYPE_SINGLE))],
    )


def test_line_split():
    check(
        "print foo:bar",
        [Token("KEYWORD"), Token("ID"), Token("NEWLINE", ":"), Token("ID")],
    )
    check("print foo:", [Token("KEYWORD"), Token("ID"), Token("NEWLINE", ":")])
    check(":foo", [Token("NEWLINE", ":"), Token("ID")])
    check("print foo:", [Token("KEYWORD"), Token("ID"), Token("NEWLINE", ":")])
    check(":foo", [Token("NEWLINE", ":"), Token("ID")])


def test_line_join():
    check(
        "foo_\nbar",
        [Token("ID", ("foo", TYPE_SINGLE), 1), Token("ID", ("bar", TYPE_SINGLE), 2)],
    )
    check(
        "foo_ \nbar",
        [Token("ID", ("foo", TYPE_SINGLE), 1), Token("ID", ("bar", TYPE_SINGLE), 2)],
    )
    check("foo_\n", Token("ID", ("foo", TYPE_SINGLE), 1))
    check("_\n", [])
    check(
        "foo_\nbar_\nbaz",
        [
            Token("ID", ("foo", TYPE_SINGLE), 1),
            Token("ID", ("bar", TYPE_SINGLE), 2),
            Token("ID", ("baz", TYPE_SINGLE), 3),
        ],
    )
