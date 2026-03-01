from collections.abc import Iterable
from enum import Enum
from typing import TYPE_CHECKING, Any

from .ply import LexToken

if TYPE_CHECKING:
    from .ast import Node


class ParseError(Exception):
    pass


class _Level(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DiagTemplate:
    counter = 1

    def __init__(self, level: _Level, message: str):
        self.number = DiagTemplate.counter
        DiagTemplate.counter += 1
        self.level = level
        self.message = message

    def level_name(self):
        return self.level.value

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


E_UNKNOWN_CHARACTERS = DiagTemplate(_Level.ERROR, "The text '{}' does not belong here.")
E_NUM_LIT_MAX_BIG = DiagTemplate(
    _Level.ERROR,
    "The number {} is too large to be represented. Allowed range is [{} to {}].",
)
E_NUM_LIT_OUTSIDE_GIVEN_RANGE = DiagTemplate(
    _Level.ERROR,
    "The number {} is outside the range of the requested type {}. "
    "Allowed range is [{} to {}].",
)
E_UNEXPECTED_ITEM = DiagTemplate(
    _Level.ERROR, "The item {} is unexpected here. Expected {} instead."
)
E_UNEXPECTED_KEYWORD = DiagTemplate(_Level.ERROR, "The keyword {} is unexpected here.")
E_KW_BAD_SIGIL = DiagTemplate(
    _Level.ERROR, "The {} suffix cannot be used on the keyword '{}'."
)
E_EXISTING_DEF_SIGIL_CLASH = DiagTemplate(
    _Level.ERROR, "The {} suffix does not match the definition of '{}'. Use {} instead."
)
E_SIGIL_WITH_AS = DiagTemplate(
    _Level.ERROR, "Type suffixes cannot be used with an AS TYPE clause."
)
E_DUPE_AS_TYPE = DiagTemplate(_Level.ERROR, "AS TYPE clause cannot be repeated.")
E_EMPTY_DIM = DiagTemplate(_Level.ERROR, "At least one variable must be defined.")
E_BAD_TYPE_WIDTH = DiagTemplate(
    _Level.ERROR, "The {} type only allows fixed-widths in range [{} to {}]."
)
E_UNFIXABLE_TYPE = DiagTemplate(
    _Level.ERROR, "The {} type cannot be specified with a fixed width."
)
E_TOO_MANY_LOOP_GUARDS = DiagTemplate(
    _Level.ERROR, "Loop cannot have conditions at both top and bottom."
)
E_TOO_MANY_ARGUMENTS = DiagTemplate(
    _Level.ERROR, "The procedure {} only takes {} arguments, but {} have been given."
)
E_NOT_ENOUGH_ARGUMENTS = DiagTemplate(
    _Level.ERROR, "The procedure {} takes {} arguments, but only {} have been given."
)
E_ARG_TYPE_MISMATCH = DiagTemplate(
    _Level.ERROR, "Argument of type {} cannot be cast to required type {}"
)
E_NO_MATCHING_OVERLOAD = DiagTemplate(
    _Level.ERROR, "{} cannot be applied to argument(s) of type {}"
)
E_EXPECTED_SUB_NOT_FUNCTION = DiagTemplate(
    _Level.ERROR, "Expected a statement, not a function."
)
E_EXPECTED_FUNCTION_NOT_SUB = DiagTemplate(
    _Level.ERROR, "Expected a function, not a statement."
)
E_ASSIGNMENT_MISMATCH = DiagTemplate(
    _Level.ERROR, "Cannot convert expression of type {} to {} for assignment"
)
E_UNPRINTABLE_TYPE = DiagTemplate(_Level.ERROR, "Cannot print expression of type {}")
E_NON_NUMERIC_CONDITION = DiagTemplate(
    _Level.ERROR, "Condition must be a numeric expression"
)
E_NON_NUMERIC_VARIABLE = DiagTemplate(_Level.ERROR, "Variable must be a numeric type")
E_NON_NUMERIC_EXPR = DiagTemplate(
    _Level.ERROR, "Expression must produce a numeric value"
)
E_EXPECTED_VAR_NAME = DiagTemplate(_Level.ERROR, "Expected a variable name")
E_FOR_NEXT_VAR_MISMATCH = DiagTemplate(
    _Level.ERROR, "Incorrect variable {}, expected {}"
)
E_CLOSE_KEYWORD_NO_OPEN = DiagTemplate(_Level.ERROR, "{} without {}")
E_NAME_IN_USE = DiagTemplate(_Level.ERROR, "{} is already defined")
E_SUB_WITH_TYPE = DiagTemplate(
    _Level.ERROR,
    "SUB declaration must not have a return type. "
    "To return a value, use FUNCTION instead.",
)
E_NESTED_PROC = DiagTemplate(
    _Level.ERROR, "Subprocedures must not be inside other subprocedures"
)
E_RETURN_MISMATCH = DiagTemplate(
    _Level.ERROR, "Cannot convert expression of type {} to {} for function return value"
)
E_BAD_METACOMMAND = DiagTemplate(_Level.ERROR, "Metacommand error on {}")
E_OVERLOAD_PROHIBITED = DiagTemplate(
    _Level.ERROR, "Subprocedure {} cannot be redefined"
)
E_NOT_A_TYPE = DiagTemplate(_Level.ERROR, "Expected a type name")
E_DUPE_USING = DiagTemplate(_Level.ERROR, "USING can only appear once in a statement")
E_USING_NON_STRING = DiagTemplate(
    _Level.ERROR, "USING must be followed by a string expression"
)
