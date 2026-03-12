from dataclasses import dataclass
from typing import Any

from .. import diagnostics as diag
from ..ast import ProcDefinition, Procedure, SymbolStore
from ..datatypes import (
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
    CompoundField,
    ExtendedFloat,
    TypeSignature,
)
from ..diagnostics import DiagnosticStore, DiagTemplate
from ..lexer import Lexer, Number


@dataclass
class Token:
    type: str
    value: Any = None
    plain_value: Any = None


def check(
    text: str,
    expecteds: Token | list[Token],
    symbols: SymbolStore | None = None,
    d: DiagTemplate | None = None,
):
    diags = DiagnosticStore()
    lex = Lexer(symbols if symbols else SymbolStore(), diags)
    lex.input(text)
    try:
        actuals = list(lex)
    except diag.DiagnosticError:
        assert d is not None and diags.has(d)
        return
    assert d is None and len(diags.diagnostics) == 0
    if isinstance(expecteds, Token):
        expecteds = [expecteds]
    assert len(actuals) == len(expecteds)
    for actual, expected in zip(actuals, expecteds):
        assert actual.type == expected.type
        if expected.value is not None:
            assert actual.value == expected.value
        if expected.plain_value is not None:
            assert actual.plain_value == expected.plain_value


def check_expr(
    text: str, expected: Token | None = None, diag: DiagTemplate | None = None
):
    expecteds = [] if expected is None else [Token("KEYWORD", "?"), expected]
    check("? " + text, expecteds, d=diag)


def check_bitn(input: str, kind: str, value: int, sigil: str):
    symbols = SymbolStore()
    lex = Lexer(symbols, DiagnosticStore())
    lex.input("? " + input)
    actuals = list(lex)
    assert len(actuals) == 2
    assert actuals[1].type == kind
    assert actuals[1].value.value == value
    assert actuals[1].value.type == symbols.lookup_sigil(sigil)


def test_int_lit_type_detection():
    check_expr("123", Token("NUM_LIT", Number(123, TYPE_INTEGER)))
    check_expr("32767", Token("NUM_LIT", Number(32767, TYPE_INTEGER)))
    check_expr("32768", Token("NUM_LIT", Number(32768, TYPE_LONG)))
    check_expr("2147483647", Token("NUM_LIT", Number(2147483647, TYPE_LONG)))
    check_expr("2147483648", Token("NUM_LIT", Number(2147483648, TYPE__INTEGER64)))
    check_expr(
        "9223372036854775807",
        Token("NUM_LIT", Number(9223372036854775807, TYPE__INTEGER64)),
    )
    check_expr(
        "9223372036854775808",
        Token("NUM_LIT", Number(9223372036854775808, TYPE__UNSIGNED__INTEGER64)),
    )
    check_expr(
        "18446744073709551615",
        Token("NUM_LIT", Number(18446744073709551615, TYPE__UNSIGNED__INTEGER64)),
    )
    check_expr("18446744073709551616", diag=diag.E_NUM_LIT_MAX_BIG)


def test_int_lit_explicit_type():
    check_expr("0`", Token("NUM_LIT", Number(0, TYPE__BIT, sigil="`")))
    check_expr("1`", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr("0~`", Token("NUM_LIT", Number(0, TYPE__UNSIGNED__BIT, sigil="~`")))
    check_expr("1~`", Token("NUM_LIT", Number(1, TYPE__UNSIGNED__BIT, sigil="~`")))
    check_expr("2~`", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr("127%%", Token("NUM_LIT", Number(0x7F, TYPE__BYTE, sigil="%%")))
    check_expr("128%%", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr(
        "128~%%", Token("NUM_LIT", Number(0x80, TYPE__UNSIGNED__BYTE, sigil="~%%"))
    )
    check_expr("256~%%", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr("32767%", Token("NUM_LIT", Number(0x7FFF, TYPE_INTEGER, sigil="%")))
    check_expr("32768%", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr(
        "32768~%", Token("NUM_LIT", Number(0x8000, TYPE__UNSIGNED_INTEGER, sigil="~%"))
    )
    check_expr(
        "65535~%", Token("NUM_LIT", Number(0xFFFF, TYPE__UNSIGNED_INTEGER, sigil="~%"))
    )
    check_expr("65536%", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr(
        "2147483647&", Token("NUM_LIT", Number(0x7FFFFFFF, TYPE_LONG, sigil="&"))
    )
    check_expr("2147483648&", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr(
        "2147483648~&",
        Token("NUM_LIT", Number(0x80000000, TYPE__UNSIGNED_LONG, sigil="~&")),
    )
    check_expr(
        "4294967295~&",
        Token("NUM_LIT", Number(0xFFFFFFFF, TYPE__UNSIGNED_LONG, sigil="~&")),
    )
    check_expr("4294967296~&", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr(
        "9223372036854775807&&",
        Token("NUM_LIT", Number(0x7FFFFFFFFFFFFFFF, TYPE__INTEGER64, sigil="&&")),
    )
    check_expr(
        "9223372036854775808&&",
        Token("ERROR"),
        diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE,
    )
    check_expr(
        "9223372036854775808~&&",
        Token(
            "NUM_LIT",
            Number(0x8000000000000000, TYPE__UNSIGNED__INTEGER64, sigil="~&&"),
        ),
    )
    check_expr(
        "18446744073709551615~&&",
        Token(
            "NUM_LIT",
            Number(0xFFFFFFFFFFFFFFFF, TYPE__UNSIGNED__INTEGER64, sigil="~&&"),
        ),
    )
    check_expr(
        "18446744073709551616~&&",
        Token("ERROR"),
        diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE,
    )
    check_expr("1&&", Token("NUM_LIT", Number(1, TYPE__INTEGER64, sigil="&&")))


def test_int_lit_explicit_float_type():
    check_expr("2!", Token("NUM_LIT", Number(2, TYPE_SINGLE, sigil="!")))
    check_expr("2#", Token("NUM_LIT", Number(2, TYPE_DOUBLE, sigil="#")))
    check_expr(
        "2##", Token("NUM_LIT", Number(ExtendedFloat("2"), TYPE__FLOAT, sigil="##"))
    )


def test_dec_lit():
    check_expr("1.25", Token("NUM_LIT", Number(1.25, TYPE_SINGLE, Number.Style.DEC)))
    check_expr(".25", Token("NUM_LIT", Number(0.25, TYPE_SINGLE, Number.Style.DEC)))
    check_expr("23.", Token("NUM_LIT", Number(23.0, TYPE_SINGLE, Number.Style.DEC)))


def test_dec_lit_type_detection():
    check_expr(
        "1.234567", Token("NUM_LIT", Number(1.234567, TYPE_SINGLE, Number.Style.DEC))
    )
    check_expr(
        "1.2345678", Token("NUM_LIT", Number(1.2345678, TYPE_DOUBLE, Number.Style.DEC))
    )
    check_expr(
        "12345678.", Token("NUM_LIT", Number(12345678.0, TYPE_DOUBLE, Number.Style.DEC))
    )
    check_expr(
        ".1234567890123456",
        Token("NUM_LIT", Number(0.1234567890123456, TYPE_DOUBLE, Number.Style.DEC)),
    )
    check_expr(
        ".12345678901234567",
        Token(
            "NUM_LIT",
            Number(ExtendedFloat(".12345678901234567"), TYPE__FLOAT, Number.Style.DEC),
        ),
    )


def test_dec_lit_explicit_type():
    check_expr(
        "123456789012345678901234567890123456789.0!",
        Token(
            "NUM_LIT", Number(1.2345678901234568e38, TYPE_SINGLE, Number.Style.DEC, "!")
        ),
    )
    check_expr(
        "123456789012345678901234567890123456789.0#",
        Token(
            "NUM_LIT", Number(1.2345678901234568e38, TYPE_DOUBLE, Number.Style.DEC, "#")
        ),
    )
    check_expr(
        "1234567890123456789012345678901234567890.0!",
        Token("ERROR"),
        diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE,
    )
    check_expr(
        "1234567890123456789012345678901234567890.0#",
        Token(
            "NUM_LIT", Number(1.2345678901234568e39, TYPE_DOUBLE, Number.Style.DEC, "#")
        ),
    )
    check_expr(
        "1234567890123456789012345678901234567890.0##",
        Token(
            "NUM_LIT",
            Number(
                ExtendedFloat("1.234567890123456789012345678901234567890", "39"),
                TYPE__FLOAT,
                Number.Style.DEC,
                "##",
            ),
        ),
    )


def test_base_lit():
    check_expr(
        "&H123456789ABCDEF0",
        Token(
            "NUM_LIT", Number(0x123456789ABCDEF0, TYPE__INTEGER64, Number.Style.HEXA)
        ),
    )
    check_expr("&h08", Token("NUM_LIT", Number(0x8, TYPE_INTEGER, Number.Style.HEXA)))
    check_expr(
        "&B10", Token("NUM_LIT", Number(0b10, TYPE_INTEGER, Number.Style.BINARY))
    )
    check_expr(
        "&b001", Token("NUM_LIT", Number(0b1, TYPE_INTEGER, Number.Style.BINARY))
    )
    check_expr(
        "&O12345670",
        Token("NUM_LIT", Number(0o12345670, TYPE_LONG, Number.Style.OCTAL)),
    )
    check_expr("&o002", Token("NUM_LIT", Number(0o2, TYPE_INTEGER, Number.Style.OCTAL)))


def test_base_lit_type_detection():
    check_expr("&h0", Token("NUM_LIT", Number(0, TYPE_INTEGER, Number.Style.HEXA)))
    check_expr(
        "&h7fff", Token("NUM_LIT", Number(0x7FFF, TYPE_INTEGER, Number.Style.HEXA))
    )
    # This behaviour is whacky, probably deserves a warning
    check_expr(
        "&h8000", Token("NUM_LIT", Number(-0x8000, TYPE_INTEGER, Number.Style.HEXA))
    )
    check_expr(
        "&hDEAD", Token("NUM_LIT", Number(-8531, TYPE_INTEGER, Number.Style.HEXA))
    )
    check_expr(
        "&h7fffffff", Token("NUM_LIT", Number(0x7FFFFFFF, TYPE_LONG, Number.Style.HEXA))
    )
    check_expr(
        "&h80000000",
        Token("NUM_LIT", Number(-0x80000000, TYPE_LONG, Number.Style.HEXA)),
    )
    check_expr(
        "&h7fffffffffffffff",
        Token(
            "NUM_LIT", Number(0x7FFFFFFFFFFFFFFF, TYPE__INTEGER64, Number.Style.HEXA)
        ),
    )
    check_expr(
        "&h8000000000000000",
        Token(
            "NUM_LIT", Number(-0x8000000000000000, TYPE__INTEGER64, Number.Style.HEXA)
        ),
    )
    check_expr(
        "&hffffffffffffffff",
        Token("NUM_LIT", Number(-1, TYPE__INTEGER64, Number.Style.HEXA)),
    )
    check_expr("&h10000000000000000", diag=diag.E_NUM_LIT_MAX_BIG)


def test_base_lit_explicit_bitn():
    check_bitn("&b1`1", "NUM_LIT", -1, "`1")
    check_expr("&b10`1", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_bitn("&b1`4", "NUM_LIT", 1, "`4")
    check_bitn("&b1010`4", "NUM_LIT", -6, "`4")
    check_bitn("&b1~`1", "NUM_LIT", 1, "~`1")
    check_expr("&b10~`1", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_bitn("&b1010~`4", "NUM_LIT", 10, "~`4")


def test_base_lit_explicit_type():
    check_expr(
        "&b0`", Token("NUM_LIT", Number(0, TYPE__BIT, Number.Style.BINARY, sigil="`"))
    )
    check_expr(
        "&b1`", Token("NUM_LIT", Number(-1, TYPE__BIT, Number.Style.BINARY, sigil="`"))
    )
    check_expr("&b10`", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr(
        "&o0~`",
        Token(
            "NUM_LIT", Number(0, TYPE__UNSIGNED__BIT, Number.Style.OCTAL, sigil="~`")
        ),
    )
    check_expr(
        "&o1~`",
        Token(
            "NUM_LIT", Number(1, TYPE__UNSIGNED__BIT, Number.Style.OCTAL, sigil="~`")
        ),
    )
    check_expr("&o2~`", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr(
        "&h7f%%",
        Token("NUM_LIT", Number(0x7F, TYPE__BYTE, Number.Style.HEXA, sigil="%%")),
    )
    check_expr(
        "&h80%%",
        Token("NUM_LIT", Number(-0x80, TYPE__BYTE, Number.Style.HEXA, sigil="%%")),
    )
    check_expr(
        "&h80~%%",
        Token(
            "NUM_LIT",
            Number(0x80, TYPE__UNSIGNED__BYTE, Number.Style.HEXA, sigil="~%%"),
        ),
    )
    check_expr("&h100~%%", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr(
        "&h7fff%",
        Token("NUM_LIT", Number(0x7FFF, TYPE_INTEGER, Number.Style.HEXA, sigil="%")),
    )
    check_expr(
        "&h8000%",
        Token("NUM_LIT", Number(-0x8000, TYPE_INTEGER, Number.Style.HEXA, sigil="%")),
    )
    check_expr(
        "&h8000~%",
        Token(
            "NUM_LIT",
            Number(0x8000, TYPE__UNSIGNED_INTEGER, Number.Style.HEXA, sigil="~%"),
        ),
    )
    check_expr(
        "&hffff~%",
        Token(
            "NUM_LIT",
            Number(0xFFFF, TYPE__UNSIGNED_INTEGER, Number.Style.HEXA, sigil="~%"),
        ),
    )
    check_expr("&h10000%", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr(
        "&h7fffffff&",
        Token("NUM_LIT", Number(0x7FFFFFFF, TYPE_LONG, Number.Style.HEXA, sigil="&")),
    )
    check_expr(
        "&h80000000&",
        Token("NUM_LIT", Number(-0x80000000, TYPE_LONG, Number.Style.HEXA, sigil="&")),
    )
    check_expr(
        "&h80000000~&",
        Token(
            "NUM_LIT",
            Number(0x80000000, TYPE__UNSIGNED_LONG, Number.Style.HEXA, sigil="~&"),
        ),
    )
    check_expr(
        "&hffffffff~&",
        Token(
            "NUM_LIT",
            Number(0xFFFFFFFF, TYPE__UNSIGNED_LONG, Number.Style.HEXA, sigil="~&"),
        ),
    )
    check_expr("&h100000000~&", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)
    check_expr(
        "&h7fffffffffffffff&&",
        Token(
            "NUM_LIT",
            Number(0x7FFFFFFFFFFFFFFF, TYPE__INTEGER64, Number.Style.HEXA, sigil="&&"),
        ),
    )
    check_expr(
        "&h8000000000000000&&",
        Token(
            "NUM_LIT",
            Number(-0x8000000000000000, TYPE__INTEGER64, Number.Style.HEXA, sigil="&&"),
        ),
    )
    check_expr(
        "&h8000000000000000~&&",
        Token(
            "NUM_LIT",
            Number(
                0x8000000000000000,
                TYPE__UNSIGNED__INTEGER64,
                Number.Style.HEXA,
                sigil="~&&",
            ),
        ),
    )
    check_expr(
        "&hffffffffffffffff~&&",
        Token(
            "NUM_LIT",
            Number(
                0xFFFFFFFFFFFFFFFF,
                TYPE__UNSIGNED__INTEGER64,
                Number.Style.HEXA,
                sigil="~&&",
            ),
        ),
    )
    check_expr(
        "&h10000000000000000~&&",
        Token("ERROR"),
        diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE,
    )
    check_expr(
        "&b1&&",
        Token("NUM_LIT", Number(1, TYPE__INTEGER64, Number.Style.BINARY, sigil="&&")),
    )


def test_exp_e_lit():
    expected_type = TYPE_SINGLE
    for c in "e", "E":
        check_expr(
            f"17{c}2", Token("NUM_LIT", Number(1700, expected_type, Number.Style.EXP))
        )
        check_expr(
            f"17.25{c}2",
            Token("NUM_LIT", Number(1725, expected_type, Number.Style.EXP)),
        )
        check_expr(
            f"1.725{c}+2",
            Token("NUM_LIT", Number(172.5, expected_type, Number.Style.EXP)),
        )
        check_expr(
            f".1725{c}2",
            Token("NUM_LIT", Number(17.25, expected_type, Number.Style.EXP)),
        )
        check_expr(
            f".1725{c}10",
            Token("NUM_LIT", Number(0.1725e10, expected_type, Number.Style.EXP)),
        )
        check_expr(
            f"17{c}", Token("NUM_LIT", Number(17, expected_type, Number.Style.EXP))
        )
        check_expr(
            f"17.25{c}",
            Token("NUM_LIT", Number(17.25, expected_type, Number.Style.EXP)),
        )
        check_expr(
            f".25{c}", Token("NUM_LIT", Number(0.25, expected_type, Number.Style.EXP))
        )
        check_expr(
            f"25.{c}", Token("NUM_LIT", Number(25, expected_type, Number.Style.EXP))
        )
        check_expr(
            f"25{c}-2", Token("NUM_LIT", Number(0.25, expected_type, Number.Style.EXP))
        )
        check_expr(
            f"2.5{c}-10",
            Token("NUM_LIT", Number(2.5e-10, expected_type, Number.Style.EXP)),
        )
    check_expr("3e39", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)


def test_exp_d_lit():
    expected_type = TYPE_DOUBLE
    for c in "d", "D":
        check_expr(
            f"17{c}2", Token("NUM_LIT", Number(1700, expected_type, Number.Style.EXP))
        )
        check_expr(
            f"17.25{c}2",
            Token("NUM_LIT", Number(1725, expected_type, Number.Style.EXP)),
        )
        check_expr(
            f"1.725{c}+2",
            Token("NUM_LIT", Number(172.5, expected_type, Number.Style.EXP)),
        )
        check_expr(
            f".1725{c}2",
            Token("NUM_LIT", Number(17.25, expected_type, Number.Style.EXP)),
        )
        check_expr(
            f".1725{c}10",
            Token("NUM_LIT", Number(0.1725e10, expected_type, Number.Style.EXP)),
        )
        check_expr(
            f"17{c}", Token("NUM_LIT", Number(17, expected_type, Number.Style.EXP))
        )
        check_expr(
            f"17.25{c}",
            Token("NUM_LIT", Number(17.25, expected_type, Number.Style.EXP)),
        )
        check_expr(
            f".25{c}", Token("NUM_LIT", Number(0.25, expected_type, Number.Style.EXP))
        )
        check_expr(
            f"25.{c}", Token("NUM_LIT", Number(25, expected_type, Number.Style.EXP))
        )
        check_expr(
            f"25{c}-2", Token("NUM_LIT", Number(0.25, expected_type, Number.Style.EXP))
        )
        check_expr(
            f"2.5{c}-10",
            Token("NUM_LIT", Number(2.5e-10, expected_type, Number.Style.EXP)),
        )
    check_expr("1.8d308", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)


def test_exp_f_lit():
    expected_type = TYPE__FLOAT
    for c in "f", "F":
        check_expr(
            f"17{c}2",
            Token(
                "NUM_LIT",
                Number(ExtendedFloat("1700"), expected_type, Number.Style.EXP),
            ),
        )
        check_expr(
            f"17.25{c}2",
            Token(
                "NUM_LIT",
                Number(ExtendedFloat("1725"), expected_type, Number.Style.EXP),
            ),
        )
        check_expr(
            f"1.725{c}+2",
            Token(
                "NUM_LIT",
                Number(ExtendedFloat("172.5"), expected_type, Number.Style.EXP),
            ),
        )
        check_expr(
            f".1725{c}2",
            Token(
                "NUM_LIT",
                Number(ExtendedFloat("17.25"), expected_type, Number.Style.EXP),
            ),
        )
        check_expr(
            f".1725{c}10",
            Token(
                "NUM_LIT",
                Number(ExtendedFloat("1.725", "9"), expected_type, Number.Style.EXP),
            ),
        )
        check_expr(
            f"17{c}",
            Token(
                "NUM_LIT", Number(ExtendedFloat("17"), expected_type, Number.Style.EXP)
            ),
        )
        check_expr(
            f"17.25{c}",
            Token(
                "NUM_LIT",
                Number(ExtendedFloat("17.25"), expected_type, Number.Style.EXP),
            ),
        )
        check_expr(
            f".25{c}",
            Token(
                "NUM_LIT", Number(ExtendedFloat(".25"), expected_type, Number.Style.EXP)
            ),
        )
        check_expr(
            f"25.{c}",
            Token(
                "NUM_LIT", Number(ExtendedFloat("25"), expected_type, Number.Style.EXP)
            ),
        )
        check_expr(
            f"25{c}-2",
            Token(
                "NUM_LIT",
                Number(ExtendedFloat("2.5", "-1"), expected_type, Number.Style.EXP),
            ),
        )
        check_expr(
            f"2.5{c}-10",
            Token(
                "NUM_LIT",
                Number(ExtendedFloat("2.5", "-10"), expected_type, Number.Style.EXP),
            ),
        )
    check_expr("1.2f4932", diag=diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE)


def test_string_lit():
    check_expr(r'"hello"', Token("STRING_LIT", r"hello"))


def test_keyword():
    check("?", Token("KEYWORD", "?"))
    check("if", Token("KEYWORD", "if"))
    check("if%", [], d=diag.E_KW_BAD_SIGIL)
    check("if$", Token("ID", ("if", TYPE_STRING, "$")))


def test_procedure():
    symbols = SymbolStore()
    a_sub = Procedure(
        "a_sub",
        "A_Sub",
        [
            ProcDefinition(
                "a_sub",
                TypeSignature(TYPE__NONE, []),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            )
        ],
    )
    a_function = Procedure(
        "a_function",
        "A_Function",
        [
            ProcDefinition(
                "a_function",
                TypeSignature(TYPE_STRING, []),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            )
        ],
    )
    a_string_builtin = Procedure(
        "a_string_builtin$",
        "A_String_Builtin$",
        [
            ProcDefinition(
                "a_string_builtin$",
                TypeSignature(TYPE_STRING, []),
                decl_only=True,
                lex_start=-1,
                lex_end=-1,
            )
        ],
    )
    symbols.procedures["a_sub"] = a_sub
    symbols.procedures["a_function"] = a_function
    symbols.procedures["a_string_builtin$"] = a_string_builtin

    check("a_sub", Token("PROCEDURE", a_sub), symbols)
    check("a_sub!", [], symbols, d=diag.E_EXISTING_DEF_SIGIL_CLASH)
    check("a_function", Token("PROCEDURE", a_function), symbols)
    check("a_function$", Token("PROCEDURE", a_function), symbols)
    check("a_function!", [], symbols, d=diag.E_EXISTING_DEF_SIGIL_CLASH)
    check(
        "a_string_builtin",
        Token("ID", ("a_string_builtin", TYPE_SINGLE, None)),
        symbols,
    )
    check("a_string_builtin$", Token("PROCEDURE", a_string_builtin), symbols)


def test_id():
    check("Foo", Token("ID", ("foo", TYPE_SINGLE, None)))
    check("Foo_bar", Token("ID", ("foo_bar", TYPE_SINGLE, None)))
    check("_foo", Token("ID", ("_foo", TYPE_SINGLE, None)))
    check("foo23x", Token("ID", ("foo23x", TYPE_SINGLE, None)))


def test_dotted_id():
    check("foo.bar", Token("ID", ("foo.bar", TYPE_SINGLE, None)))
    check("foo.bar.baz!", Token("ID", ("foo.bar.baz", TYPE_SINGLE, "!")))


def test_dotted_variable():
    symbols = SymbolStore()
    type = symbols.create_compound_type("t", "t", [CompoundField(TYPE_LONG, "a", "a")])
    var = symbols.create_local("foo", "foo", type)

    check(
        "foo.bar",
        [Token("VARIABLE", var), Token("DOTTED_ID", "bar", ".bar")],
        symbols=symbols,
    )
    check(
        "foo.bar.baz",
        [
            Token("VARIABLE", var),
            Token("DOTTED_ID", "bar", ".bar"),
            Token("DOTTED_ID", "baz", ".baz"),
        ],
        symbols=symbols,
    )


def test_id_builtin_sigil():
    check("foo`", Token("ID", ("foo", TYPE__BIT, "`")))
    check("foo%%", Token("ID", ("foo", TYPE__BYTE, "%%")))
    check("foo%", Token("ID", ("foo", TYPE_INTEGER, "%")))
    check("foo&", Token("ID", ("foo", TYPE_LONG, "&")))
    check("foo&&", Token("ID", ("foo", TYPE__INTEGER64, "&&")))
    # check("foo%&", Token("ID", ("foo", BUILTIN_TYPES["_offset"])))
    check("foo~`", Token("ID", ("foo", TYPE__UNSIGNED__BIT, "~`")))
    check("foo~%%", Token("ID", ("foo", TYPE__UNSIGNED__BYTE, "~%%")))
    check("foo~%", Token("ID", ("foo", TYPE__UNSIGNED_INTEGER, "~%")))
    check("foo~&", Token("ID", ("foo", TYPE__UNSIGNED_LONG, "~&")))
    check("foo~&&", Token("ID", ("foo", TYPE__UNSIGNED__INTEGER64, "~&&")))
    # check("foo~%&", Token("ID", ("foo", BUILTIN_TYPES["_unsigned _offset"])))
    check("foo!", Token("ID", ("foo", TYPE_SINGLE, "!")))
    check("foo#", Token("ID", ("foo", TYPE_DOUBLE, "#")))
    check("foo##", Token("ID", ("foo", TYPE__FLOAT, "##")))
    check("foo$", Token("ID", ("foo", TYPE_STRING, "$")))


def test_id_custom_sigil():
    def check_custom_sigil(input: str, type_name: str):
        symbols = SymbolStore()
        lex = Lexer(symbols, DiagnosticStore())
        lex.input(input)
        result = list(lex)[0]
        type = symbols.find_type(type_name)
        assert type is not None
        assert result.type == "ID"
        assert result.value == ("foo", type, type.sigil)

    check_custom_sigil("foo`10", "_bit * 10")
    check_custom_sigil("foo~`10", "_unsigned _bit * 10")
    check_custom_sigil("foo$10", "string * 10")
    check_expr("foo$0", diag=diag.E_BAD_TYPE_WIDTH)
    check_expr("foo`65", diag=diag.E_BAD_TYPE_WIDTH)
    check_expr("foo~`65", diag=diag.E_BAD_TYPE_WIDTH)


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
    check("'foo", Token("NEWLINE", "'", "'foo"))
    check("this ' comment", [Token("ID"), Token("NEWLINE", "'", "' comment")])
    check("that '", [Token("ID"), Token("NEWLINE", "'", "'")])
    check("'foo\n", Token("NEWLINE", "'", "'foo\n"))
    check("this ' comment\n", [Token("ID"), Token("NEWLINE", "'", "' comment\n")])
    check("that '\n  ", [Token("ID"), Token("NEWLINE", "'", "'\n")])


def test_remark():
    check("rem foo", Token("NEWLINE", "rem", "rem foo"))
    check("foo REM", [Token("ID"), Token("NEWLINE", "rem", "REM")])
    check("rem foo\n", Token("NEWLINE", "rem", "rem foo\n"))
    check("foo REM\n  ", [Token("ID"), Token("NEWLINE", "rem", "REM\n")])
    check("rem1 rema rem.x", [Token("ID"), Token("ID"), Token("ID")])


def test_line_label():
    check("foo:", Token("LINE_LABEL", "foo"))
    check("foo :", Token("LINE_LABEL", "foo"))
    check(
        "foo: bar",
        [Token("LINE_LABEL", "foo"), Token("ID", ("bar", TYPE_SINGLE, None))],
    )
    check("foo.bar23:", Token("LINE_LABEL", "foo.bar23"))


def test_line_num():
    check("123", Token("LINE_NUM", "123"))
    check("123foo", [Token("LINE_NUM", "123"), Token("ID", ("foo", TYPE_SINGLE, None))])
    check(
        "123 foo", [Token("LINE_NUM", "123"), Token("ID", ("foo", TYPE_SINGLE, None))]
    )


def test_line_num_label():
    check("123 foo:", Token("LINE_NUM_LABEL", ("123", "foo")))
    check(
        "123foo:bar",
        [
            Token("LINE_NUM_LABEL", ("123", "foo")),
            Token("ID", ("bar", TYPE_SINGLE, None)),
        ],
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
        [
            Token("ID", ("foo", TYPE_SINGLE, None)),
            Token("ID", ("bar", TYPE_SINGLE, None)),
        ],
    )
    check(
        "foo_ \nbar",
        [
            Token("ID", ("foo", TYPE_SINGLE, None)),
            Token("ID", ("bar", TYPE_SINGLE, None)),
        ],
    )
    check("foo_\n", Token("ID", ("foo", TYPE_SINGLE, None)))
    check("_\n", [])
    check(
        "foo_\nbar_\nbaz",
        [
            Token("ID", ("foo", TYPE_SINGLE, None)),
            Token("ID", ("bar", TYPE_SINGLE, None)),
            Token("ID", ("baz", TYPE_SINGLE, None)),
        ],
    )


def test_bad_character():
    check(
        '@ "hello"',
        [],
        d=diag.E_UNKNOWN_CHARACTERS,
    )
    check(
        '? "hello""',
        [],
        d=diag.E_UNKNOWN_CHARACTERS,
    )


def test_metacommand():
    check("$foo", Token("META_CMD", ("$foo", None)))
    check("$foo:bar", Token("META_CMD", ("$foo", "bar")))
    check("  $foo  :  bar", Token("META_CMD", ("$foo", "bar")))


def test_commented_metacommand():
    check("'$dynamic", Token("META_CMD", ("$dynamic", None)))
    check(
        "'$dynamic\nprint",
        [
            Token("META_CMD", ("$dynamic", None)),
            Token("NEWLINE"),
            Token("KEYWORD", "print"),
        ],
    )
    check(
        "'$dynamic $static",
        [Token("META_CMD", ("$dynamic", None)), Token("META_CMD", ("$static", None))],
    )
    check(
        "'$dynamic lskdjf $static",
        [Token("META_CMD", ("$dynamic", None)), Token("META_CMD", ("$static", None))],
    )


def test_remmed_metacommand():
    check("rem $dynamic", Token("META_CMD", ("$dynamic", None)))


def test_fake_commented_metacommand():
    check("'$foobar\n", Token("NEWLINE"))
    check("'$dynamic $spatz", [Token("META_CMD", ("$dynamic", None))])


def test_include_metacommand():
    check("'$include", Token("META_CMD", ("$include", None)))
    check("'$include:''", Token("META_CMD", ("$include", "")))
    check("'$include:'foo'", Token("META_CMD", ("$include", "foo")))
    check(" rem  $include  : 'foo'asdf", Token("META_CMD", ("$include", "foo")))
    check(
        "'$include:'foo' $include:'bar'",
        [
            Token("META_CMD", ("$include", "foo")),
            Token("META_CMD", ("$include", "bar")),
        ],
    )


def test_type_name():
    check("single", Token("TYPE", TYPE_SINGLE))
    check("_bit", Token("TYPE", TYPE__BIT))


def test_type_name_bad_sigil():
    check("single!", [], d=diag.E_KW_BAD_SIGIL)


def test_type_name_string_name():
    check("single$", Token("ID", ("single", TYPE_STRING, "$")))


def test_paren_array_detection():
    symbols = SymbolStore()
    type = symbols.lookup_array_type(TYPE_SINGLE, 1)
    array_var = symbols.create_local("foo", "foo", type)
    scalar_var = symbols.create_local("foo", "foo", TYPE_SINGLE)
    check(
        "foo +2",
        [Token("VARIABLE", scalar_var), Token("PUNCTUATION", "+"), Token("NUM_LIT")],
        symbols=symbols,
    )
    check(
        "foo (2",
        [Token("VARIABLE", array_var), Token("PUNCTUATION", "("), Token("NUM_LIT")],
        symbols=symbols,
    )
