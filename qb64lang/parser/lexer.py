import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Literal, cast

from . import diagnostics as diag
from .ast import SymbolStore
from .datatypes import (
    TYPE__BIT,
    TYPE__FLOAT,
    TYPE__INTEGER64,
    TYPE__NONE,
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
    # COMMENT only returned when dealing with commented metacommands.
    # Normally returned as NEWLINE.
    "COMMENT",
    "REMARK",  # Returned as NEWLINE
    "LINE_SPLIT",  # Returned as NEWLINE
    "META_CMD",
    "LINE_NUM",
    "LINE_LABEL",
    "LINE_NUM_LABEL",
    "ID",
    # ID may be returned as ID, KEYWORD, VARIABLE, PROCEDURE or TYPE
    # depending on symbol lookups.
    "KEYWORD",
    "VARIABLE",
    "PROCEDURE",
    "TYPE",
    "DOTTED_ID",
    "STRING_LIT",
    "NUM_LIT",
    "BASE_LIT",  # Returned as NUM_LIT
    "EXP_LIT",  # Returned as NUM_LIT
    "DEC_LIT",  # Returned as NUM_LIT
    "INT_LIT",  # Returned as NUM_LIT
    "PUNCTUATION",
    "BAD_CHAR",
)

states = (("meta", "exclusive"), ("dotted", "exclusive"))

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


@dataclass
class Number:
    class Style(Enum):
        BINARY = auto()
        OCTAL = auto()
        HEXA = auto()
        EXP = auto()
        DEC = auto()
        INT = auto()

    value: int | float | ExtendedFloat
    type: Type
    style: Style = Style.INT
    sigil: str | None = None


@dataclass
class Id:
    name: str
    type: Type
    sigil: str | None
    is_array: bool = False


def Lexer(symbols: SymbolStore, diags: diag.DiagnosticStore):
    def t_ANY_error(t: LexToken):
        t.lexer.skip(len(t.value))
        diags.raise_error(diag.E_UNKNOWN_CHARACTERS, t, t.value)

    @Token(nl)
    def t_NEWLINE(t: LexToken):
        t.value = "\n"
        return t

    @Token(r"'(?P<comment_text>.*(\n|$))")
    def t_COMMENT(t: LexToken):
        text = t.lexer.lexmatch.group("comment_text")
        if text.lstrip(" \t").startswith("$"):
            t.lexer.lexpos = t.lexpos + 1
            t.lexer.begin("meta")
            t.type = "COMMENT"
            t.value = ("'", None)
            return t
        t.type = "NEWLINE"
        t.value = "'"
        return t

    @Token(r"REM(?P<remark_text>([^0-9a-zA-Z.\n].*)?(\n|$))")
    def t_REMARK(t: LexToken):
        text = t.lexer.lexmatch.group("remark_text")
        if text.lstrip(" \t").startswith("$"):
            t.lexer.lexpos = t.lexpos + 3
            t.lexer.begin("meta")
            t.type = "COMMENT"
            t.value = (t.value[:3].lower(), None)
            return t
        t.type = "NEWLINE"
        t.value = "rem"
        return t

    @Token(rf"{ws}*(?P<metacmd_a>\${id_body}){ws}*(:{ws}*'(?P<metacmd_b>[^']*)')?")
    def t_meta_META_CMD(t: LexToken):
        cmd: str
        arg: str | None
        cmd, arg = t.lexer.lexmatch.group("metacmd_a", "metacmd_b")
        if cmd.lower() in ["$static", "$dynamic", "$include"]:
            t.value = (cmd.lower(), arg)
        else:
            t.type = "COMMENT"
            t.value = (None, t.plain_value)
        return t

    @Token(nl)
    def t_meta_NEWLINE(t: LexToken):
        t.value = "\n"
        t.lexer.begin("INITIAL")
        return t

    @Token("[^$]+")
    def t_meta_COMMENT(t: LexToken):
        t.value = (None, t.value)
        return t

    @Token(rf"^{ws}*(?P<metacmd_c>\${id_body}){ws}*(:{ws}*(?P<metacmd_d>.*))?")
    def t_META_CMD(t: LexToken):
        t.value = t.lexer.lexmatch.group("metacmd_c", "metacmd_d")
        return t

    @Token(
        f"^{ws}*(?P<linenumlabel_a>{digit}+){ws}*(?P<linenumlabel_b>{id_body}){ws}*:"
    )
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
        # No token produced
        pass

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
            t.value = Number(value, type, style=Number.Style.EXP)
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
        if base == 16:
            t.value.style = Number.Style.HEXA
        elif base == 8:
            t.value.style = Number.Style.OCTAL
        elif base == 2:
            t.value.style = Number.Style.BINARY
        t.value.sigil = sigil
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
        t.value.style = Number.Style.DEC
        t.value.sigil = sigil
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
        t.value.style = Number.Style.INT
        t.value.sigil = sigil
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
                ({ws}*\()?
        """
    )
    def t_ID(t: LexToken):
        name: str = t.lexer.lexmatch.group("id_name").lower()
        sigil: str | None = t.lexer.lexmatch.group("id_sigil")
        if sigil is not None:
            validate_sigil(sigil, t, diags)
        is_array = False
        if t.value.endswith("("):
            # '(' is trailing context to indicate the ID is an array
            is_array = True
            t.value = t.value.rstrip(" (")
            t.plain_value = t.plain_value[0 : len(t.value)]
            t.lexend = t.lexpos + len(t.value)
            t.lexer.lexpos -= 1

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

        if proc_tok := lookup_proc(name, sigil, symbols, t, diags):
            t.type = proc_tok[0]
            t.value = proc_tok[1]
            t.value.is_array = is_array
            return t
        elif not symbols.return_var_as_id and (
            var := symbols.find_variable(
                name, symbols.lookup_sigil(sigil) if sigil else None, as_array=is_array
            )
        ):
            t.type = "VARIABLE"
            t.value = var
            return t
        elif "." in name:
            # Return a in `a.b.c` if it is a known VARIABLE. Otherwise
            # return the entire `a.b.c` as an ID.
            i = name.find(".")
            stem = name[:i]
            if not symbols.return_var_as_id and (
                var := symbols.find_variable(stem, None)
            ):
                t.plain_value = t.plain_value[:i]
                t.lexer.lexpos = t.lexpos + i
                t.lexend = t.lexpos + i
                t.lexer.begin("dotted")
                t.type = "VARIABLE"
                t.value = var
                return t

        # otherwise remain as ID
        t.value = Id(
            name,
            symbols.lookup_sigil(sigil) if sigil else symbols.default_type,
            sigil,
            is_array,
        )
        return t

    @Token(rf"\.({letter}|{digit}|\.|_)*")
    def t_dotted_ID(t: LexToken):
        t.type = "DOTTED_ID"
        name: str = t.value
        i = name.find(".", 1)
        if i == -1:
            t.lexer.begin("INITIAL")
            t.value = name[1:]
            return t
        t.value = name[1:i]
        t.plain_value = name[:i]
        t.lexer.lexpos = t.lexpos + i
        t.lexend = t.lexpos + i
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

    return lex(reflags=re.VERBOSE | re.IGNORECASE | re.MULTILINE)


def detect_base_int_type(value: int) -> Number | None:
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
            return Number(value, signed)
        if unsigned.min <= value <= unsigned.max:
            return Number(-int(unsigned.max) + value - 1, signed)
    return None


def constrain_base_int_value(value: int, type: IntegralType) -> Number | None:
    if type.min <= value <= type.max:
        return Number(value, type)
    if type.min < 0 and value <= type.max * 2 + 1:
        return Number(value - (int(type.max) * 2 + 1) - 1, type)
    return None


def detect_dec_lit_type(value: str) -> Number:
    num_digits = len(value) - 1
    if num_digits <= 7:
        return Number(float(value), TYPE_SINGLE)
    if num_digits <= 16:
        return Number(float(value), TYPE_DOUBLE)
    return Number(ExtendedFloat(value), TYPE__FLOAT)


def constrain_dec_lit_value(value: str, type: FloatType) -> Number | None:
    v = float(value)
    inf = float("inf")
    if type == TYPE_SINGLE:
        if v != inf and type.min <= v <= type.max:
            return Number(v, type)
    elif type == TYPE_DOUBLE:
        if v != inf:
            return Number(v, type)
    elif type == TYPE__FLOAT:
        return Number(ExtendedFloat(value), type)
    return None


def detect_int_lit_type(value: int) -> Number | None:
    for type in [TYPE_INTEGER, TYPE_LONG, TYPE__INTEGER64, TYPE__UNSIGNED__INTEGER64]:
        if type.min <= value <= type.max:
            return Number(value, type)
    return None


def constrain_int_lit_value(
    value: int, type: IntegralType | FloatType
) -> Number | None:
    if type == TYPE__FLOAT:
        return Number(ExtendedFloat(str(value)), type)
    if type.min <= value <= type.max:
        return Number(value, type)
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


def lookup_proc(
    name: str,
    sigil: str | None,
    symbols: SymbolStore,
    t: LexToken,
    diags: diag.DiagnosticStore,
):
    proc_plain = symbols.find_procedure(name)
    proc_string = symbols.find_procedure(name + "$")

    def bad_sigil_error():
        alts = set[str]()
        if proc_plain:
            for impl in proc_plain.impls:
                ret = impl.signature.ret
                if not (impl.strictsigil and ret != TYPE_STRING) and ret != TYPE__NONE:
                    alts.add(ret.sigil)
        if proc_string:
            alts.add("$")
        alts.add("no suffix")
        alts = list(alts)
        alts.sort()

        diags.raise_error(
            diag.E_EXISTING_DEF_SIGIL_CLASH,
            t,
            sigil,
            t.lexer.lexmatch.group("id_name"),
            " or ".join(alts),
        )

    if symbols.return_proc_as_id and (proc_plain or proc_string):
        return (
            "ID",
            Id(
                name,
                symbols.lookup_sigil(sigil) if sigil else symbols.default_type,
                sigil,
            ),
        )

    if sigil is None:
        if proc_plain is None:
            return None
        # All impls are either non-strictsigil or non-string strictsigil
        # because the proc name did not end in $. In either case we are
        # compatible so no further checks needed.
        return ("PROCEDURE", proc_plain)

    elif sigil == "$":
        # Check for string strictsigil
        if proc_string:
            # All impls are string strictsigil because the proc name ends
            # in $ so we are compatible.
            return ("PROCEDURE", proc_string)
        # Check for non-strictsigil
        if proc_plain:
            for impl in proc_plain.impls:
                if impl.signature.ret == TYPE_STRING:
                    return ("PROCEDURE", proc_plain)
        return None

    # Non-string sigil case
    if proc_plain is None:
        return None
    type = symbols.lookup_sigil(sigil)
    for impl in proc_plain.impls:
        if type == impl.signature.ret and not impl.strictsigil:
            return ("PROCEDURE", proc_plain)
    bad_sigil_error()
