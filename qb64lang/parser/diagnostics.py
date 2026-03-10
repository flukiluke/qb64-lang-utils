from collections.abc import Iterable
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from .ply import LexToken

if TYPE_CHECKING:
    from .ast import Node


class ParseError(Exception):
    pass


class DiagLevel(Enum):
    # Syntactic error
    ERR_SYN = auto()
    # Semantic error
    ERR_SEM = auto()
    WARNING = auto()
    INFO = auto()


class DiagTemplate:
    counter = 1

    def __init__(self, level: DiagLevel, message: str):
        self.number = DiagTemplate.counter
        DiagTemplate.counter += 1
        self.level = level
        self.message = message

    def level_name(self):
        match self.level:
            case DiagLevel.ERR_SYN | DiagLevel.ERR_SEM:
                return "error"
            case DiagLevel.WARNING:
                return "warning"
            case DiagLevel.INFO:
                return "info"

    def id(self):
        return self.level_name()[0].upper() + str(self.number).rjust(4, "0")


class _Diagnostic:
    def __init__(self, template: DiagTemplate, startpos: int, endpos: int, *args: Any):
        self.startpos = startpos
        self.endpos = endpos
        self.template = template
        human_args = self.humanise(args)
        self.message = template.message.format(*human_args)

    def humanise(self, args: Iterable[Any]):
        result = list[str]()
        for arg in args:
            if isinstance(arg, str):
                result.append(arg.replace("\n", "<newline>").replace("\t", "<tab>"))
            else:
                result.append(arg)
        return result

    def __repr__(self):
        if self.startpos == -1 or self.endpos == -1:
            location = "<unknown location>"
        else:
            location = f"{self.startpos}-{self.endpos}"
        return (
            f"{location}: {self.template.level_name()} "
            f"{self.template.id()}: {self.message}"
        )


class DiagnosticError(Exception):
    def __init__(self, diagnostic: _Diagnostic, source: LexToken):
        self.diagnostic = diagnostic
        self.source = source


class DiagnosticStore:
    def __init__(self):
        self.diagnostics = list[_Diagnostic]()

    def create(self, template: DiagTemplate, source: "LexToken | Node", *args: Any):
        if isinstance(source, LexToken):
            diag = _Diagnostic(template, source.lexpos, source.lexend, *args)
        else:
            diag = _Diagnostic(template, source.lex_start, source.lex_end, *args)
        self.diagnostics.append(diag)
        return diag

    def raise_error(self, template: DiagTemplate, source: LexToken, *args: Any):
        diag = _Diagnostic(template, source.lexpos, source.lexend, *args)
        self.diagnostics.append(diag)
        raise DiagnosticError(diag, source)

    def has(self, template: DiagTemplate):
        return any(diag.template == template for diag in self.diagnostics)

    def has_none(self):
        return len(self.diagnostics) == 0

    def sort(self):
        self.diagnostics.sort(key=lambda d: d.startpos)


E_UNKNOWN_CHARACTERS = DiagTemplate(
    DiagLevel.ERR_SYN, "The text '{}' does not belong here."
)
E_NUM_LIT_MAX_BIG = DiagTemplate(
    DiagLevel.ERR_SYN,
    "The number {} is too large to be represented. Allowed range is [{} to {}].",
)
E_NUM_LIT_OUTSIDE_GIVEN_RANGE = DiagTemplate(
    DiagLevel.ERR_SYN,
    "The number {} is outside the range of the requested type {}. "
    "Allowed range is [{} to {}].",
)
E_UNEXPECTED_ITEM = DiagTemplate(
    DiagLevel.ERR_SYN, "The item {} is unexpected here. Expected {} instead."
)
E_UNEXPECTED_KEYWORD = DiagTemplate(
    DiagLevel.ERR_SYN, "The keyword {} is unexpected here."
)
E_KW_BAD_SIGIL = DiagTemplate(
    DiagLevel.ERR_SYN, "The {} suffix cannot be used on the keyword '{}'."
)
E_EXISTING_DEF_SIGIL_CLASH = DiagTemplate(
    DiagLevel.ERR_SYN,
    "The {} suffix does not match the definition of '{}'. Use {} instead.",
)
E_SIGIL_WITH_AS = DiagTemplate(
    DiagLevel.ERR_SYN, "Type suffixes cannot be used with an AS TYPE clause."
)
E_SIGIL_WITH_TYPE_NAME = DiagTemplate(
    DiagLevel.ERR_SYN, "Type suffixes cannot be used with a custom type name."
)
E_SIGIL_WITH_FIELD_NAME = DiagTemplate(
    DiagLevel.ERR_SYN, "Type suffixes cannot be used with a field of a custom type."
)
E_MISSING_AS_TYPE = DiagTemplate(DiagLevel.ERR_SYN, "AS TYPE clause must be present.")
E_DUPE_AS_TYPE = DiagTemplate(DiagLevel.ERR_SYN, "AS TYPE clause cannot be repeated.")
E_EMPTY_DIM = DiagTemplate(DiagLevel.ERR_SYN, "At least one variable must be defined.")
E_EMPTY_COMPOUND = DiagTemplate(
    DiagLevel.ERR_SEM, "Custom type must have at least one field."
)
E_DUPE_COMPOUND_FIELD = DiagTemplate(
    DiagLevel.ERR_SEM, "The field {} is already defined."
)
E_BAD_TYPE_WIDTH = DiagTemplate(
    DiagLevel.ERR_SYN, "The {} type only allows fixed-widths in range [{} to {}]."
)
E_UNFIXABLE_TYPE = DiagTemplate(
    DiagLevel.ERR_SYN, "The {} type cannot be specified with a fixed width."
)
E_TOO_MANY_LOOP_GUARDS = DiagTemplate(
    DiagLevel.ERR_SEM, "Loop cannot have conditions at both top and bottom."
)
E_TOO_MANY_ARGUMENTS = DiagTemplate(
    DiagLevel.ERR_SEM,
    "The procedure {} only takes {} arguments, but {} have been given.",
)
E_NOT_ENOUGH_ARGUMENTS = DiagTemplate(
    DiagLevel.ERR_SEM,
    "The procedure {} takes {} arguments, but only {} have been given.",
)
E_ARG_TYPE_MISMATCH = DiagTemplate(
    DiagLevel.ERR_SEM, "Argument of type {} cannot be cast to required type {}"
)
E_NO_MATCHING_OVERLOAD = DiagTemplate(
    DiagLevel.ERR_SEM, "{} cannot be applied to argument(s) of type {}"
)
E_EXPECTED_SUB_NOT_FUNCTION = DiagTemplate(
    DiagLevel.ERR_SEM, "Expected a statement, not a function."
)
E_EXPECTED_FUNCTION_NOT_SUB = DiagTemplate(
    DiagLevel.ERR_SEM, "Expected a function, not a statement."
)
E_ASSIGNMENT_MISMATCH = DiagTemplate(
    DiagLevel.ERR_SEM, "Cannot convert expression of type {} to {} for assignment"
)
E_UNPRINTABLE_TYPE = DiagTemplate(
    DiagLevel.ERR_SEM, "Cannot print expression of type {}"
)
E_NON_NUMERIC_CONDITION = DiagTemplate(
    DiagLevel.ERR_SEM, "Condition must be a numeric expression"
)
E_NON_NUMERIC_VARIABLE = DiagTemplate(
    DiagLevel.ERR_SEM, "Variable must be a numeric type"
)
E_NON_NUMERIC_EXPR = DiagTemplate(
    DiagLevel.ERR_SEM, "Expression must produce a numeric value"
)
E_EXPECTED_VAR_NAME = DiagTemplate(DiagLevel.ERR_SYN, "Expected a variable name")
E_FOR_NEXT_VAR_MISMATCH = DiagTemplate(
    DiagLevel.ERR_SYN, "Incorrect variable {}, expected {}"
)
E_CLOSE_KEYWORD_NO_OPEN = DiagTemplate(DiagLevel.ERR_SYN, "{} without {}")
E_NAME_IN_USE = DiagTemplate(DiagLevel.ERR_SYN, "{} is already defined")
E_SUB_WITH_TYPE = DiagTemplate(
    DiagLevel.ERR_SEM,
    "SUB declaration must not have a return type. "
    "To return a value, use FUNCTION instead.",
)
E_RETURN_MISMATCH = DiagTemplate(
    DiagLevel.ERR_SEM,
    "Cannot convert expression of type {} to {} for function return value",
)
E_BAD_METACOMMAND = DiagTemplate(DiagLevel.ERR_SYN, "Metacommand error on {}")
E_OVERLOAD_PROHIBITED = DiagTemplate(
    DiagLevel.ERR_SYN, "Subprocedure {} cannot be redefined"
)
E_NOT_A_TYPE = DiagTemplate(DiagLevel.ERR_SYN, "Expected a type name")
E_DUPE_USING = DiagTemplate(
    DiagLevel.ERR_SYN, "USING can only appear once in a statement"
)
E_USING_NON_STRING = DiagTemplate(
    DiagLevel.ERR_SEM, "USING must be followed by a string expression"
)
E_UNFOUND_PROC = DiagTemplate(DiagLevel.ERR_SYN, "Proc not registered")
E_NOT_TOPLEVEL = DiagTemplate(
    DiagLevel.ERR_SYN, "{} keyword cannot be nested inside other statements."
)
E_DOT_PROHIBITED = DiagTemplate(DiagLevel.ERR_SYN, "Dot is not allowed in the name {}")
E_FIELD_ACCESS_NON_COMPOUND = DiagTemplate(
    DiagLevel.ERR_SYN, "Cannot access field {} on non-compound type {}."
)
E_UNKNOWN_FIELD = DiagTemplate(
    DiagLevel.ERR_SYN, "The field {} does not exist in the type {}."
)
