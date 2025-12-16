from collections.abc import Iterable

from qbparse.ast import BuiltinProcDefinition as BPD
from qbparse.ast import ProcDefinition
from qbparse.datatypes import (
    FLOAT_TYPES,
    INTEGRAL_TYPES,
    TYPE__BYTE,
    TYPE__FLOAT,
    TYPE_ANY,
    TYPE_STRING,
    Type,
)
from qbparse.datatypes import TypeSignature as TS
from qbparse.symbols import Procedure as P


def _generic(
    ret: Type | None, params: list[Type | None], concretes: Iterable[Type]
) -> list[ProcDefinition]:
    results = list[ProcDefinition]()
    for concrete in concretes:
        results.append(
            BPD(TS(ret if ret else concrete, [p if p else concrete for p in params]))
        )
    return results


KEYWORDS = set(
    [
        # Declarations
        "dim",
        "as",
        "const",
        "sub",
        "function",
        # Conditionals
        "if",
        "then",
        "else",
        "elseif",
        "endif",
        "end",
        # Loops
        "do",
        "while",
        "loop",
        "wend",
        # Flow control
        "goto",
        "exit",
        # Operators
        "imp",
        "eqv",
        "xor",
        "or",
        "and",
        "not",
        "mod",
        # I/O
        "print",
        "?",
    ]
)

PROCS = [
    # Comparison operators
    P("=", [BPD(TS(TYPE__BYTE, [TYPE_ANY, TYPE_ANY]))]),
    P(
        "<>",
        [
            BPD(TS(TYPE__BYTE, [TYPE_STRING, TYPE_STRING])),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    P(
        "<",
        [
            BPD(TS(TYPE__BYTE, [TYPE_STRING, TYPE_STRING])),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    P(
        ">",
        [
            BPD(TS(TYPE__BYTE, [TYPE_STRING, TYPE_STRING])),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    P(
        "<=",
        [
            BPD(TS(TYPE__BYTE, [TYPE_STRING, TYPE_STRING])),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    P(
        ">=",
        [
            BPD(TS(TYPE__BYTE, [TYPE_STRING, TYPE_STRING])),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    # Arithmetic
    P(
        "+",
        [
            BPD(TS(TYPE_STRING, [TYPE_STRING, TYPE_STRING])),
            *_generic(None, [None, None], INTEGRAL_TYPES),
            *_generic(None, [None, None], FLOAT_TYPES),
        ],
    ),
    P(
        "-",
        [
            *_generic(None, [None], INTEGRAL_TYPES),
            *_generic(None, [None], FLOAT_TYPES),
            *_generic(None, [None, None], INTEGRAL_TYPES),
            *_generic(None, [None, None], FLOAT_TYPES),
        ],
    ),
    P(
        "*",
        [
            *_generic(None, [None, None], INTEGRAL_TYPES),
            *_generic(None, [None, None], FLOAT_TYPES),
        ],
    ),
    P("/", [*_generic(None, [None, None], FLOAT_TYPES)]),
    P("\\", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    P("^", [*_generic(None, [None, None], FLOAT_TYPES)]),
    P("mod", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    # Bitwise relations
    P("imp", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    P("eqv", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    P("xor", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    P("or", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    P("and", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    P("not", [*_generic(None, [None], INTEGRAL_TYPES)]),
    # Everything else
    P("val", [BPD(TS(TYPE__FLOAT, [TYPE_STRING]))]),
    P("lcase$", [BPD(TS(TYPE_STRING, [TYPE_STRING]))]),
]
