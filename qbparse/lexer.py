import re

from ply.lex import LexToken, Token, lex

from qbparse.datatypes import BUILTIN_TYPES, Type
from qbparse.symbols import SymbolStore

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
    "BASE_LIT",
    "EXP_LIT",
    "DEC_LIT",
    "INT_LIT",
    "PUNCTUATION",
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


def Lexer(symbols: SymbolStore):
    t_ignore = ws

    def t_error(t: LexToken):
        t.type = "ERROR"
        t.lexer.skip(len(t.value))
        return t

    @Token(nl)
    def t_NEWLINE(t: LexToken):
        t.lexer.lineno += 1
        t.value = "\n"
        return t

    @Token(r"'.*(\n|$)")
    def t_COMMENT(t: LexToken):
        t.type = "NEWLINE"
        t.value = "'"
        return t

    @Token(rf"REM({ws}+.*)?(\n|$)")
    def t_REMARK(t: LexToken):
        t.type = "NEWLINE"
        t.value = "rem"
        return t

    @Token(f"^{ws}*(?P<n>{digit}+){ws}*(?P<l>{id_body}){ws}*:")
    def t_LINE_NUM_LABEL(t: LexToken):
        t.value = t.lexer.lexmatch.group("n", "l")
        return t

    @Token(f"^{ws}*(?P<a>{digit}+)")
    def t_LINE_NUM(t: LexToken):
        t.value = t.lexer.lexmatch.group("a")
        return t

    @Token(f"^{ws}*(?P<a>{id_body}){ws}*:")
    def t_LINE_LABEL(t: LexToken):
        t.value = t.lexer.lexmatch.group("a")
        return t

    @Token(":")
    def t_LINE_SPLIT(t: LexToken):
        t.type = "NEWLINE"
        return t

    @Token(f"_{ws}*{nl}")
    def t_LINE_JOIN(t: LexToken):
        t.lexer.lineno += 1
        # No token produced

    @Token('"(?P<s>[^"\r\n]*)"')
    def t_STRING_LIT(t: LexToken):
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
        match = t.lexer.lexmatch
        mantissa = match.group("man")
        exp_sign = match.group("sign") or "+"
        exp = match.group("exp") or "0"
        if match.group("flag") in ["e", "E"]:
            type = symbols.lookup_sigil("!")
        elif match.group("flag") in ["d", "D"]:
            type = symbols.lookup_sigil("#")
        else:
            t.value = (
                build_float_literal(mantissa, exp_sign, exp),
                symbols.lookup_sigil("##"),
            )
            return t
        value = float(f"{mantissa}e{exp_sign}{exp}")
        if type.min <= value <= type.max:
            t.value = (value, type)
        else:
            t.type = "ERROR"
            t.value = "Literal outside range of requested type"
        return t

    @Token(
        rf"""(?P<num>&H[0-9A-Fa-f]+
                    |&O[0-7]+
                    |&B[01]+)
              (?P<sigil>~?(`{digit}*|%%|&&|%&|%|&))?
        """
    )
    def t_BASE_LIT(t: LexToken):
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
        try:
            if sigil is None:
                t.value = detect_base_int_type(value)
            else:
                t.value = constrain_base_int_value(value, symbols.lookup_sigil(sigil))
        except ValueError:
            t.type = "ERROR"
            t.value = "Literal outside range of requested type"
        return t

    @Token(rf"\.{digit}+|{digit}+\.{digit}*")
    def t_DEC_LIT(t: LexToken):
        t.value = float(t.value)
        return t

    @Token(f"{digit}+")
    def t_INT_LIT(t: LexToken):
        t.value = int(t.value)
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
        name = t.lexer.lexmatch.group("name").lower()
        sigil = t.lexer.lexmatch.group("sigil")
        if symbols.is_keyword(name):
            # Keywords with a $ are no longer keywords, hence `if$ = ""` and
            # `if$3 = ""` are acceptable but `if% = 3` is not.
            if sigil is None:
                t.type = "KEYWORD"
                t.value = name
                return t
            elif not sigil.startswith("$"):
                t.type = "ERROR"
                t.lexer.skip(len(t.value))
                return t
            # case of sigil "$" falls through below
        if proc := symbols.find_procedure(name):
            if sigil is not None:
                # The sigil must match the existing procedure, if present
                typ = symbols.lookup_sigil(sigil)
                if proc.signature and typ != proc.signature.ret:
                    t.type = "ERROR"
                    return t
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
                        | <  | > | =
                        | \( | \)
                        | \* | / 
                        | \^ | \\
                        | \+ | -
                        | ;  | ,
                        | \. | [#]
    """)
    def t_PUNCTUATION(t: LexToken):
        return t

    return lex(reflags=re.VERBOSE | re.IGNORECASE)


def build_float_literal(mantissa: str, exp_sign: str, exp: str) -> tuple[int, int]:
    """
    A Python float can't store the 80 bit extended precision type needed to support
    _FLOAT, so represent them as (mantissa, exponent) tuples where both parts are
    integers.
    """
    int_exp = int(exp)
    if exp_sign == "-":
        int_exp *= -1
    index = mantissa.find(".")
    if index >= 0:
        int_mantissa = int(mantissa.replace(".", "", count=1))
        int_exp += index - len(mantissa) + 1
    else:
        int_mantissa = int(mantissa)
    return (int_mantissa, int_exp)


def detect_base_int_type(value: int) -> tuple[int, Type]:
    """
    Identify the type of a value using rules for base notation numbers,
    returning the type and the number. Raise ValueError if number is outside
    the representable range.
    """
    for type_name in ["integer", "long", "_integer64"]:
        type = BUILTIN_TYPES[type_name]
        if type.min <= value <= type.max:
            return (value, type)
        unsigned_type = BUILTIN_TYPES["_unsigned " + type_name]
        if unsigned_type.min <= value <= unsigned_type.max:
            return (-int(unsigned_type.max) + value - 1, type)
    raise ValueError()


def constrain_base_int_value(value: int, type: Type) -> tuple[int, Type]:
    if type.min <= value <= type.max:
        return (value, type)
    if type.min < 0 and value <= type.max * 2 + 1:
        return (value - (int(type.max) * 2 + 1) - 1, type)
    raise ValueError()
