from collections.abc import Iterable

from qbparse.ast import BuiltinProcDefinition as BPD
from qbparse.ast import ProcDefinition
from qbparse.datatypes import (
    FLOAT_TYPES,
    INTEGRAL_TYPES,
    TYPE__BYTE,
    TYPE__FLOAT,
    TYPE__INTEGER64,
    TYPE_ANY,
    TYPE_STRING,
    Parameter,
    Type,
)
from qbparse.datatypes import Parameter as P
from qbparse.datatypes import TypeSignature as TS
from qbparse.symbols import Procedure as Pr


def _generic(
    ret: Type | None, params: list[Parameter | None], concretes: Iterable[Type]
) -> list[ProcDefinition]:
    results = list[ProcDefinition]()
    for concrete in concretes:
        results.append(
            BPD(TS(ret if ret else concrete, [p if p else P(concrete) for p in params]))
        )
    return results


KEYWORDS = set(
    [
        # Misc
        "to",
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
        "until",
        "loop",
        "wend",
        "for",
        "next",
        "step",
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
    Pr("=", [BPD(TS(TYPE__BYTE, [P(TYPE_ANY), P(TYPE_ANY)]))]),
    Pr("<>", [BPD(TS(TYPE__BYTE, [P(TYPE_ANY), P(TYPE_ANY)]))]),
    Pr(
        "<",
        [
            BPD(TS(TYPE__BYTE, [P(TYPE_STRING), P(TYPE_STRING)])),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    Pr(
        ">",
        [
            BPD(TS(TYPE__BYTE, [P(TYPE_STRING), P(TYPE_STRING)])),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    Pr(
        "<=",
        [
            BPD(TS(TYPE__BYTE, [P(TYPE_STRING), P(TYPE_STRING)])),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    Pr(
        ">=",
        [
            BPD(TS(TYPE__BYTE, [P(TYPE_STRING), P(TYPE_STRING)])),
            *_generic(TYPE__BYTE, [None, None], INTEGRAL_TYPES),
            *_generic(TYPE__BYTE, [None, None], FLOAT_TYPES),
        ],
    ),
    # Arithmetic
    Pr(
        "+",
        [
            BPD(TS(TYPE_STRING, [P(TYPE_STRING), P(TYPE_STRING)])),
            *_generic(None, [None, None], INTEGRAL_TYPES),
            *_generic(None, [None, None], FLOAT_TYPES),
        ],
    ),
    Pr(
        "-",
        [
            *_generic(None, [None], INTEGRAL_TYPES),
            *_generic(None, [None], FLOAT_TYPES),
            *_generic(None, [None, None], INTEGRAL_TYPES),
            *_generic(None, [None, None], FLOAT_TYPES),
        ],
    ),
    Pr(
        "*",
        [
            *_generic(None, [None, None], INTEGRAL_TYPES),
            *_generic(None, [None, None], FLOAT_TYPES),
        ],
    ),
    Pr("/", [*_generic(None, [None, None], FLOAT_TYPES)]),
    Pr("\\", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Pr("^", [*_generic(None, [None, None], FLOAT_TYPES)]),
    Pr("mod", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    # Bitwise relations
    Pr("imp", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Pr("eqv", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Pr("xor", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Pr("or", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Pr("and", [*_generic(None, [None, None], INTEGRAL_TYPES)]),
    Pr("not", [*_generic(None, [None], INTEGRAL_TYPES)]),
    # Other maths
    Pr("_atan2", [*_generic(None, [None, None], FLOAT_TYPES)]),
    # Everything else
    Pr("val", [BPD(TS(TYPE__FLOAT, [P(TYPE_STRING)]))]),
    Pr("lcase$", [BPD(TS(TYPE_STRING, [P(TYPE_STRING)]))]),
    Pr("left$", [BPD(TS(TYPE_STRING, [P(TYPE_STRING), P(TYPE__INTEGER64)]))]),
]
