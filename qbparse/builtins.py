from qbparse.datatypes import (
    TYPE__BYTE,
    TYPE__FLOAT,
    TYPE__GEN_FLOAT,
    TYPE__GEN_INT,
    TYPE__GEN_T,
    TYPE_STRING,
)
from qbparse.datatypes import TypeSignature as TS
from qbparse.procedure import BuiltinProcedure as BP

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
    BP("=", [TS(TYPE__BYTE, [TYPE__GEN_T, TYPE__GEN_T])]),
    BP(
        "<>",
        [
            TS(TYPE__BYTE, [TYPE_STRING, TYPE_STRING]),
            TS(TYPE__BYTE, [TYPE__GEN_INT, TYPE__GEN_INT]),
            TS(TYPE__BYTE, [TYPE__GEN_FLOAT, TYPE__GEN_FLOAT]),
        ],
    ),
    BP(
        "<",
        [
            TS(TYPE__BYTE, [TYPE_STRING, TYPE_STRING]),
            TS(TYPE__BYTE, [TYPE__GEN_INT, TYPE__GEN_INT]),
            TS(TYPE__BYTE, [TYPE__GEN_FLOAT, TYPE__GEN_FLOAT]),
        ],
    ),
    BP(
        ">",
        [
            TS(TYPE__BYTE, [TYPE_STRING, TYPE_STRING]),
            TS(TYPE__BYTE, [TYPE__GEN_INT, TYPE__GEN_INT]),
            TS(TYPE__BYTE, [TYPE__GEN_FLOAT, TYPE__GEN_FLOAT]),
        ],
    ),
    BP(
        "<=",
        [
            TS(TYPE__BYTE, [TYPE_STRING, TYPE_STRING]),
            TS(TYPE__BYTE, [TYPE__GEN_INT, TYPE__GEN_INT]),
            TS(TYPE__BYTE, [TYPE__GEN_FLOAT, TYPE__GEN_FLOAT]),
        ],
    ),
    BP(
        ">=",
        [
            TS(TYPE__BYTE, [TYPE_STRING, TYPE_STRING]),
            TS(TYPE__BYTE, [TYPE__GEN_INT, TYPE__GEN_INT]),
            TS(TYPE__BYTE, [TYPE__GEN_FLOAT, TYPE__GEN_FLOAT]),
        ],
    ),
    # Arithmetic
    BP(
        "+",
        [
            TS(TYPE_STRING, [TYPE_STRING, TYPE_STRING]),
            TS(TYPE__GEN_INT, [TYPE__GEN_INT, TYPE__GEN_INT]),
            TS(TYPE__GEN_FLOAT, [TYPE__GEN_FLOAT, TYPE__GEN_FLOAT]),
        ],
    ),
    BP(
        "-",
        [
            TS(TYPE__GEN_INT, [TYPE__GEN_INT]),
            TS(TYPE__GEN_FLOAT, [TYPE__GEN_FLOAT]),
            TS(TYPE__GEN_INT, [TYPE__GEN_INT, TYPE__GEN_INT]),
            TS(TYPE__GEN_FLOAT, [TYPE__GEN_FLOAT, TYPE__GEN_FLOAT]),
        ],
    ),
    BP(
        "*",
        [
            TS(TYPE__GEN_INT, [TYPE__GEN_INT, TYPE__GEN_INT]),
            TS(TYPE__GEN_FLOAT, [TYPE__GEN_FLOAT, TYPE__GEN_FLOAT]),
        ],
    ),
    BP("/", [TS(TYPE__GEN_FLOAT, [TYPE__GEN_FLOAT, TYPE__GEN_FLOAT])]),
    BP("\\", [TS(TYPE__GEN_INT, [TYPE__GEN_INT, TYPE__GEN_INT])]),
    BP("^", [TS(TYPE__GEN_FLOAT, [TYPE__GEN_FLOAT, TYPE__GEN_FLOAT])]),
    BP("mod", [TS(TYPE__GEN_INT, [TYPE__GEN_INT, TYPE__GEN_INT])]),
    # Bitwise relations
    BP("imp", [TS(TYPE__GEN_INT, [TYPE__GEN_INT, TYPE__GEN_INT])]),
    BP("eqv", [TS(TYPE__GEN_INT, [TYPE__GEN_INT, TYPE__GEN_INT])]),
    BP("xor", [TS(TYPE__GEN_INT, [TYPE__GEN_INT, TYPE__GEN_INT])]),
    BP("or", [TS(TYPE__GEN_INT, [TYPE__GEN_INT, TYPE__GEN_INT])]),
    BP("and", [TS(TYPE__GEN_INT, [TYPE__GEN_INT, TYPE__GEN_INT])]),
    BP("not", [TS(TYPE__GEN_INT, [TYPE__GEN_INT])]),
    # Everything else
    BP("val", [TS(TYPE__FLOAT, [TYPE_STRING])]),
    BP("lcase$", [TS(TYPE_STRING, [TYPE_STRING])]),
]
