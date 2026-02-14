import re
from typing import Literal, cast

from . import diagnostics as diag
from .ast import SymbolStore
from .datatypes import (
    TYPE__BIT,
    TYPE__FLOAT,
    TYPE__INTEGER64,
    TYPE__UNSIGNED__BIT,
    TYPE__UNSIGNED__INTEGER64,
    TYPE__UNSIGNED_INTEGER,
    TYPE__UNSIGNED_LONG,
    TYPE_DOUBLE,
    TYPE_INTEGER,
    TYPE_LONG,
    TYPE_SINGLE,
    TYPE_STRING,
    ExtendedFloat,
    FloatType,
    IntegralType,
    Type,
    validate_fixed_width,
)
from .ply import LexToken, Token, lex

# pyright: reportUnusedFunction=false, reportUnusedVariable=false
# ruff: noqa: F841

tokens = (
    "NEWLINE",
    "END_OF_INPUT",
    "END_OF_FILE",
    "ERROR",
    "COMMENT",
    "REMARK",
    "META_CMD",
    "LINE_SPLIT",
    "LINE_NUM",
    "LINE_LABEL",
    "LINE_NUM_LABEL",
    "ID",
    "KEYWORD",
    "VARIABLE",
    "PROCEDURE",
    "TYPE",
    "STRING_LIT",
    "NUM_LIT",
    "BASE_LIT",
    "EXP_LIT",
    "DEC_LIT",
    "INT_LIT",
    "PUNCTUATION",
    "BAD_CHAR",
)

states = (("meta", "exclusive"),)

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
    def t_ANY_error(t: LexToken):
        t.lexer.skip(t.length)
        diags.raise_error(diag.E_UNKNOWN_CHARACTERS, t, t.value)

    @Token(nl)
    def t_NEWLINE(t: LexToken):
        t.lexer.lineno += 1
        t.value = "\n"
        return t

    @Token(r"'.*(\n|$)")
    def t_COMMENT(t: LexToken):
        if t.length > 1:
            line: str = t.value
            line = line[1:].lstrip(" \t")
            if line.startswith("$"):
                t.lexer.lexpos = t.lexpos + 1
                t.lexer.begin("meta")
                return None
        t.type = "NEWLINE"
        t.value = "'"
        return t

    @Token(rf"REM({ws}+.*)?(\n|$)")
    def t_REMARK(t: LexToken):
        if t.length > 3:
            line: str = t.value
            line = line[3:].lstrip(" \t")
            if line.startswith("$"):
                t.lexer.lexpos = t.lexpos + 3
                t.lexer.begin("meta")
                return None
        t.type = "NEWLINE"
        t.value = "rem"
        return t

    @Token(rf"{ws}*(?P<metacmd_a>\${id_body}){ws}*(:{ws}*'(?P<metacmd_b>[^']*)')?")
    def t_meta_META_CMD(t: LexToken):
        cmd: str
        arg: str | None
        cmd, arg = t.lexer.lexmatch.group("metacmd_a", "metacmd_b")
        if cmd.lower() in ["$static", "$dynamic", "$include"]:
            t.value = (cmd, arg)
            return t

    @Token(nl)
    def t_meta_NEWLINE(t: LexToken):
        t.lexer.lineno += 1
        t.value = "\n"
        t.lexer.begin("INITIAL")
        return t

    @Token("[^$]+")
    def t_meta_COMMENT(t: LexToken):
        pass

    @Token(rf"^{ws}*(?P<metacmd_c>\${id_body}){ws}*(:{ws}*(?P<metacmd_d>.*))?")
    def t_META_CMD(t: LexToken):
        t.value = t.lexer.lexmatch.group("metacmd_c", "metacmd_d")
        return t

    @Token(f"^{ws}*(?P<linenumlabel_a>{digit}+){ws}*(?P<linenumlabel_b>{id_body}){ws}*:")
    def t_LINE_NUM_LABEL(t: LexToken):
        t.value = t.lexer.lexmatch.group("linenumlabel_a", "linenumlabel_b")
        return t

    @Token(f"^{ws}*(?P<linenum_a>{digit}+)")
    def t_LINE_NUM(t: LexToken):
        t.value = t.lexer.lexmatch.group("linenum_a")
        return t

    @Token(f"^{ws}*(?P<linelabel_a>{id_body}){ws}*:")
    def t_LINE_LABEL(t: LexToken):
        t.value = t.lexer.lexmatch.group("linelabel_a")
        return t

    @Token(":")
    def t_LINE_SPLIT(t: LexToken):
        t.type = "NEWLINE"
        return t

    @Token(f"_{ws}*{nl}")
    def t_LINE_JOIN(t: LexToken):
        t.lexer.lineno += 1
        # No token produced

    @Token('"(?P<stringlit_a>[^"\r\n]*)"')
    def t_STRING_LIT(t: LexToken):
        t.value = t.lexer.lexmatch.group("stringlit_a")
        return t

    @Token(
        rf"""(?P<explit_man>\.{digit}+        # Decimal leading, or
                | {digit}+             # integer leading
                    \.?{digit}*)       # with optional decimal part.
                (?P<explit_flag>D|E|F|d|e|f)  # Mandatory exponent flag.
                (?P<explit_sign>\+|-)?        # Optional exponent sign.
                (?P<explit_exp>{digit}*)      # Optional exponent
        """
    )
    def t_EXP_LIT(t: LexToken):
        t.type = "NUM_LIT"
        match = t.lexer.lexmatch
        mantissa = match.group("explit_man")
        exp_sign = match.group("explit_sign") or "+"
        exp = match.group("explit_exp") or "0"
        if match.group("explit_flag") in ["e", "E"]:
            type = TYPE_SINGLE
            value = float(f"{mantissa}e{exp_sign}{exp}")
        elif match.group("explit_flag") in ["d", "D"]:
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
        rf"""(?P<baselit_num>&H[0-9A-Fa-f]+
                    |&O[0-7]+
                    |&B[01]+)
              (?P<baselit_sigil>~?(`{digit}*|%%|&&|%&|%|&))?
        """
    )
    def t_BASE_LIT(t: LexToken):
        t.type = "NUM_LIT"
        num_part = t.lexer.lexmatch.group("baselit_num")
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
        sigil = t.lexer.lexmatch.group("baselit_sigil")
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
        rf"""(?P<declit_num>\.{digit}+|{digit}+\.{digit}*)
             (?P<declit_sigil>[#][#]|[#]|!)?
        """
    )
    def t_DEC_LIT(t: LexToken):
        t.type = "NUM_LIT"
        num_part = t.lexer.lexmatch.group("declit_num")
        sigil = t.lexer.lexmatch.group("declit_sigil")
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
        rf"""(?P<intlit_num>{digit}+)
             (?P<intlit_sigil>~?(`{digit}*|%%|&&|%&|%|&|[#][#]|[#]|!))?
        """
    )
    def t_INT_LIT(t: LexToken):
        t.type = "NUM_LIT"
        num_part = int(t.lexer.lexmatch.group("intlit_num"))
        sigil = t.lexer.lexmatch.group("intlit_sigil")
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
        rf"""(?P<id_name>_*{id_body}|\?)
                # Optional sigils
                (?P<id_sigil>`{digit}*
                |%%|&&|%&|%|&
                |~`{digit}*
                |~%%|~&&|~%&|~%|~&
                |!|[#][#]|[#]
                |\${digit}*)?
        """
    )
    def t_ID(t: LexToken):
        name = t.lexer.lexmatch.group("id_name").lower()
        sigil = t.lexer.lexmatch.group("id_sigil")
        if sigil is not None:
            validate_sigil(sigil, t, diags)
        # The presence or absence of the $ is critical for detecting some builtins.
        # `if` is a keyword, but `if$ = 3` is valid. Similarly `left$` is a function,
        # but `left = 3` is valid.
        if type := symbols.find_type(name):
            if sigil is None:
                t.type = "TYPE"
                t.value = type
                return t
            elif not sigil.startswith("$"):
                diags.raise_error(
                    diag.E_KW_BAD_SIGIL, t, sigil, t.lexer.lexmatch.group("id_name")
                )
            # case of sigil "$" falls through below
        if symbols.is_keyword(name):
            if sigil is None:
                t.type = "KEYWORD"
                t.value = name
                return t
            elif not sigil.startswith("$"):
                diags.raise_error(
                    diag.E_KW_BAD_SIGIL, t, sigil, t.lexer.lexmatch.group("id_name")
                )
            # case of sigil "$" falls through below
        if (proc := symbols.find_procedure(name)) or (
            sigil == "$" and (proc := symbols.find_procedure(name + "$"))
        ):
            if symbols.return_proc_as_id:
                t.value = (name, symbols.lookup_sigil(sigil), sigil)
                return t
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
                        t.lexer.lexmatch.group("id_name"),
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
        t.value = (name, symbols.lookup_sigil(sigil), sigil)
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
        return t

    @Token(f"{ws}+")
    def t_WHITESPACE(t: LexToken):
        pass

    @Token(".")
    def t_BAD_CHAR(t: LexToken):
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
        validate_fixed_width(TYPE__BIT, int(sigil[1:]), t, diags)
    elif sigil.startswith("~`") and len(sigil) > 2:
        validate_fixed_width(TYPE__UNSIGNED__BIT, int(sigil[2:]), t, diags)
    elif sigil.startswith("$") and len(sigil) > 1:
        validate_fixed_width(TYPE_STRING, int(sigil[1:]), t, diags)
