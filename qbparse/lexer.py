import re
from typing import Literal, cast

from ply.lex import LexToken, Token, lex

import qbparse.diagnostics as diag
from qbparse.datatypes import (
    TYPE__FLOAT,
    TYPE__INTEGER64,
    TYPE__UNSIGNED__INTEGER64,
    TYPE__UNSIGNED_INTEGER,
    TYPE__UNSIGNED_LONG,
    TYPE_DOUBLE,
    TYPE_INTEGER,
    TYPE_LONG,
    TYPE_SINGLE,
    ExtendedFloat,
    FloatType,
    IntegralType,
    Type,
)
from qbparse.store import SymbolStore

# pyright: reportUnusedFunction=false, reportUnusedVariable=false
# ruff: noqa: F841

tokens = (
    "NEWLINE",
    "END_OF_INPUT",
    "END_OF_FILE",
    "ERROR",
    "COMMENT",
    "REMARK",
    "LINE_SPLIT",
    "LINE_NUM",
    "LINE_LABEL",
    "LINE_NUM_LABEL",
    "ID",
    "KEYWORD",
    "VARIABLE",
    "PROCEDURE",
    "STRING_LIT",
    "NUM_LIT",
    "BASE_LIT",
    "EXP_LIT",
    "DEC_LIT",
    "INT_LIT",
    "PUNCTUATION",
    "BAD_CHAR",
)

ws = "[ \t]"
nl = r"(?:\r?\n)"
letter = "[A-Za-z]"
digit = "[0-9]"
# Dot is valid in variable and label names.
# It is not valid in UDT or or UDT element names.
id_body = rf"""
            {letter}                        # Starting letter
            (?:
                (?:{letter}|{digit}|_|\.)*  # Medial numbers/letters/underscore/dot
                (?:{letter}|{digit})        # Final letter/number
            )?
            """


def Lexer(symbols: SymbolStore, diags: diag.DiagnosticStore):
    t_ignore = ws

    def t_error(t: LexToken):
        t.length = len(t.value)
        t.lexer.skip(t.length)
        diags.raise_error(diag.E_UNKNOWN_CHARACTERS, t, t.value)
        return t

    @Token(nl)
    def t_NEWLINE(t: LexToken):
        t.length = len(t.value)
        t.lexer.lineno += 1
        t.value = "\n"
        return t

    @Token(r"'.*(\n|$)")
    def t_COMMENT(t: LexToken):
        t.length = len(t.value)
        t.type = "NEWLINE"
        t.value = "'"
        return t

    @Token(rf"REM({ws}+.*)?(\n|$)")
    def t_REMARK(t: LexToken):
        t.length = len(t.value)
        t.type = "NEWLINE"
        t.value = "rem"
        return t

    @Token(f"^{ws}*(?P<n>{digit}+){ws}*(?P<l>{id_body}){ws}*:")
    def t_LINE_NUM_LABEL(t: LexToken):
        t.length = len(t.value)
        t.value = t.lexer.lexmatch.group("n", "l")
        return t

    @Token(f"^{ws}*(?P<a>{digit}+)")
    def t_LINE_NUM(t: LexToken):
        t.length = len(t.value)
        t.value = t.lexer.lexmatch.group("a")
        return t

    @Token(f"^{ws}*(?P<a>{id_body}){ws}*:")
    def t_LINE_LABEL(t: LexToken):
        t.length = len(t.value)
        t.value = t.lexer.lexmatch.group("a")
        return t

    @Token(":")
    def t_LINE_SPLIT(t: LexToken):
        t.length = len(t.value)
        t.type = "NEWLINE"
        return t

    @Token(f"_{ws}*{nl}")
    def t_LINE_JOIN(t: LexToken):
        t.length = len(t.value)
        t.lexer.lineno += 1
        # No token produced

    @Token('"(?P<s>[^"\r\n]*)"')
    def t_STRING_LIT(t: LexToken):
        t.length = len(t.value)
        t.value = t.lexer.lexmatch.group("s")
        return t

    @Token(
        rf"""(?P<man>\.{digit}+        # Decimal leading, or
                | {digit}+             # integer leading
                    \.?{digit}*)       # with optional decimal part.
                (?P<flag>D|E|F|d|e|f)  # Mandatory exponent flag.
                (?P<sign>\+|-)?        # Optional exponent sign.
                (?P<exp>{digit}*)      # Optional exponent
        """
    )
    def t_EXP_LIT(t: LexToken):
        t.length = len(t.value)
        t.type = "NUM_LIT"
        match = t.lexer.lexmatch
        mantissa = match.group("man")
        exp_sign = match.group("sign") or "+"
        exp = match.group("exp") or "0"
        if match.group("flag") in ["e", "E"]:
            type = TYPE_SINGLE
            value = float(f"{mantissa}e{exp_sign}{exp}")
        elif match.group("flag") in ["d", "D"]:
            type = TYPE_DOUBLE
            value = float(f"{mantissa}e{exp_sign}{exp}")
        else:
            type = TYPE__FLOAT
            value = ExtendedFloat(mantissa, exp_sign + exp)
        if type.min <= value <= type.max:
            t.value = (value, type)
        else:
            diags.raise_error(
                diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE,
                t,
                t.value,
                type.name,
                type.min,
                type.max,
            )
        return t

    @Token(
        rf"""(?P<num>&H[0-9A-Fa-f]+
                    |&O[0-7]+
                    |&B[01]+)
              (?P<sigil>~?(`{digit}*|%%|&&|%&|%|&))?
        """
    )
    def t_BASE_LIT(t: LexToken):
        t.length = len(t.value)
        t.type = "NUM_LIT"
        num_part = t.lexer.lexmatch.group("num")
        match num_part[1].upper():
            case "H":
                base = 16
            case "O":
                base = 8
            case "B":
                base = 2
            case _:
                base = 10
        value = int(num_part[2:], base)
        sigil = t.lexer.lexmatch.group("sigil")
        if sigil is None:
            t.value = detect_base_int_type(value) or diags.raise_error(
                diag.E_NUM_LIT_MAX_BIG,
                t,
                t.value,
                num_to_base(TYPE__INTEGER64.min, base),
                num_to_base(TYPE__UNSIGNED__INTEGER64.max, base),
            )
        else:
            validate_sigil(sigil, t, diags)
            type = cast(IntegralType, symbols.lookup_sigil(sigil))
            t.value = constrain_base_int_value(value, type) or diags.raise_error(
                diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE,
                t,
                t.value,
                type.name,
                num_to_base(type.min, base),
                num_to_base(type.max, base),
            )
        return t

    @Token(
        rf"""(?P<num>\.{digit}+|{digit}+\.{digit}*)
             (?P<sigil>[#][#]|[#]|!)?
        """
    )
    def t_DEC_LIT(t: LexToken):
        t.length = len(t.value)
        t.type = "NUM_LIT"
        num_part = t.lexer.lexmatch.group("num")
        sigil = t.lexer.lexmatch.group("sigil")
        if sigil is None:
            t.value = detect_dec_lit_type(num_part)
        else:
            type = cast(FloatType, symbols.lookup_sigil(sigil))
            t.value = constrain_dec_lit_value(num_part, type) or diags.raise_error(
                diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE,
                t,
                t.value,
                type.name,
                type.min,
                type.max,
            )
        return t

    @Token(
        rf"""(?P<num>{digit}+)
             (?P<sigil>~?(`{digit}*|%%|&&|%&|%|&|[#][#]|[#]|!))?
        """
    )
    def t_INT_LIT(t: LexToken):
        t.length = len(t.value)
        t.type = "NUM_LIT"
        num_part = int(t.lexer.lexmatch.group("num"))
        sigil = t.lexer.lexmatch.group("sigil")
        if sigil is None:
            t.value = detect_int_lit_type(num_part) or diags.raise_error(
                diag.E_NUM_LIT_MAX_BIG,
                t,
                t.value,
                TYPE__INTEGER64.min,
                TYPE__UNSIGNED__INTEGER64.max,
            )
        else:
            validate_sigil(sigil, t, diags)
            type = cast(IntegralType | FloatType, symbols.lookup_sigil(sigil))
            t.value = constrain_int_lit_value(
                num_part,
                type,
            ) or diags.raise_error(
                diag.E_NUM_LIT_OUTSIDE_GIVEN_RANGE,
                t,
                t.value,
                type.name,
                type.min,
                type.max,
            )
        return t

    @Token(
        rf"""(?P<name>_*{id_body}|\?)
                # Optional sigils
                (?P<sigil>`{digit}*
                |%%|&&|%&|%|&
                |~`{digit}*
                |~%%|~&&|~%&|~%|~&
                |!|[#][#]|[#]
                |\${digit}*)?
        """
    )
    def t_ID(t: LexToken):
        t.length = len(t.value)
        name = t.lexer.lexmatch.group("name").lower()
        sigil = t.lexer.lexmatch.group("sigil")
        if sigil is not None:
            validate_sigil(sigil, t, diags)
        # The presence or absence of the $ is critical for detecting some builtins.
        # `if` is a keyword, but `if$ = 3` is valid. Similarly `left$` is a function,
        # but `left = 3` is valid.
        if symbols.is_keyword(name):
            if sigil is None:
                t.type = "KEYWORD"
                t.value = name
                return t
            elif not sigil.startswith("$"):
                diags.raise_error(
                    diag.E_KW_BAD_SIGIL, t, sigil, t.lexer.lexmatch.group("name")
                )
            # case of sigil "$" falls through below
        if (proc := symbols.find_procedure(name)) or (
            sigil == "$" and (proc := symbols.find_procedure(name + "$"))
        ):
            if sigil is not None:
                # The sigil must match the existing procedure, if present
                typ = symbols.lookup_sigil(sigil)
                for sig in proc.sigs():
                    if typ == sig.ret:
                        break
                else:
                    alts = " or ".join(
                        [s.ret.sigil for s in proc.sigs() if s.ret.sigil]
                        + ["no suffix"]
                    )
                    diags.raise_error(
                        diag.E_EXISTING_DEF_SIGIL_CLASH,
                        t,
                        sigil,
                        t.lexer.lexmatch.group("name"),
                        alts,
                    )
            t.type = "PROCEDURE"
            t.value = proc
            return t
        elif var := symbols.find_variable(name, sigil):
            t.type = "VARIABLE"
            t.value = var
            return t
        # otherwise remain as ID
        t.value = (name, symbols.lookup_sigil(sigil))
        return t

    @Token(r"""<= | >= | <>
             | <  | >  | =
             | \( | \)
             | \* | / 
             | \^ | \\
             | \+ | -
             | ;  | ,
             | \. | [#]
    """)
    def t_PUNCTUATION(t: LexToken):
        t.length = len(t.value)
        return t

    @Token(".")
    def t_BAD_CHAR(t: LexToken):
        t.length = len(t.value)
        diags.raise_error(diag.E_UNKNOWN_CHARACTERS, t, t.value)

    return lex(reflags=re.VERBOSE | re.IGNORECASE)


def detect_base_int_type(value: int) -> tuple[int, Type] | None:
    """
    Identify the type of a value using rules for base notation numbers,
    returning the type and the number. Return None if number is outside
    the representable range.
    """
    for signed, unsigned in [
        (TYPE_INTEGER, TYPE__UNSIGNED_INTEGER),
        (TYPE_LONG, TYPE__UNSIGNED_LONG),
        (TYPE__INTEGER64, TYPE__UNSIGNED__INTEGER64),
    ]:
        if signed.min <= value <= signed.max:
            return (value, signed)
        if unsigned.min <= value <= unsigned.max:
            return (-int(unsigned.max) + value - 1, signed)
    return None


def constrain_base_int_value(
    value: int, type: IntegralType
) -> tuple[int, IntegralType] | None:
    if type.min <= value <= type.max:
        return (value, type)
    if type.min < 0 and value <= type.max * 2 + 1:
        return (value - (int(type.max) * 2 + 1) - 1, type)
    return None


def detect_dec_lit_type(value: str) -> tuple[float | ExtendedFloat, Type]:
    num_digits = len(value) - 1
    if num_digits <= 7:
        return (float(value), TYPE_SINGLE)
    if num_digits <= 16:
        return (float(value), TYPE_DOUBLE)
    return (ExtendedFloat(value), TYPE__FLOAT)


def constrain_dec_lit_value(
    value: str, type: FloatType
) -> tuple[float | ExtendedFloat, Type] | None:
    v = float(value)
    inf = float("inf")
    if type == TYPE_SINGLE:
        if v != inf and type.min <= v <= type.max:
            return (v, type)
    elif type == TYPE_DOUBLE:
        if v != inf:
            return (v, type)
    elif type == TYPE__FLOAT:
        return (ExtendedFloat(value), type)
    return None


def detect_int_lit_type(value: int) -> tuple[int, Type] | None:
    for type in [TYPE_INTEGER, TYPE_LONG, TYPE__INTEGER64, TYPE__UNSIGNED__INTEGER64]:
        if type.min <= value <= type.max:
            return (value, type)
    return None


def constrain_int_lit_value(
    value: int, type: IntegralType | FloatType
) -> tuple[int | ExtendedFloat, Type] | None:
    if type == TYPE__FLOAT:
        return (ExtendedFloat(str(value)), type)
    if type.min <= value <= type.max:
        return (value, type)
    return None


def num_to_base(value: int, base: Literal[2] | Literal[8] | Literal[10] | Literal[16]):
    sign = ""
    if value < 0:
        sign = "-"
    value = abs(value)
    if base == 2:
        return sign + "&B" + bin(value)[2:]
    elif base == 8:
        return sign + "&O" + oct(value)[2:]
    elif base == 10:
        return sign + str(value)
    elif base == 16:
        return sign + "&H" + hex(value)[2:].upper()


def validate_sigil(sigil: str, t: LexToken, diags: diag.DiagnosticStore):
    if sigil.startswith("`") and len(sigil) > 1:
        width = int(sigil[1:])
        if width > 64 or width < 1:
            diags.raise_error(diag.E_BAD_SIGIL_WIDTH, t, "`", 1, 64)
    elif sigil.startswith("~`") and len(sigil) > 2:
        width = int(sigil[2:])
        if width > 64 or width < 1:
            diags.raise_error(diag.E_BAD_SIGIL_WIDTH, t, "~`", 1, 64)
    elif sigil.startswith("$") and len(sigil) > 1:
        width = int(sigil[1:])
        if width > 2**64 - 1 or width < 1:
            diags.raise_error(diag.E_BAD_SIGIL_WIDTH, t, "$", 1, 2**64 - 1)
