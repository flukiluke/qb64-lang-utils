from collections.abc import Iterable
from enum import Enum
from typing import Any

from ply.lex import LexToken


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
    def __init__(self, template: DiagTemplate, startpos: int, textlen: int, *args: Any):
        self.startpos = startpos
        self.textlen = textlen
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
        return (
            f"{self.startpos}+{self.textlen}: "
            f"{self.template.level_name()} {self.template.id()}: {self.message}"
        )


class DiagnosticError(Exception):
    def __init__(self, diagnostic: _Diagnostic):
        self.diagnostic = diagnostic


class DiagnosticStore:
    def __init__(self):
        self.diagnostics = list[_Diagnostic]()

    def create(self, template: DiagTemplate, source: LexToken, *args: Any):
        diag = _Diagnostic(template, source.lexpos, source.length, *args)
        self.diagnostics.append(diag)
        return diag

    def raise_error(self, template: DiagTemplate, source: LexToken, *args: Any):
        diag = _Diagnostic(template, source.lexpos, source.length, *args)
        self.diagnostics.append(diag)
        raise DiagnosticError(diag)

    def has(self, template: DiagTemplate):
        return any(diag.template == template for diag in self.diagnostics)


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
E_BAD_SIGIL_WIDTH = DiagTemplate(
    _Level.ERROR, "The {} suffix only allows fixed-widths in range [{} to {}]."
)
E_TOO_MANY_LOOP_GUARDS = DiagTemplate(
    _Level.ERROR, "Loop cannot have conditions at both top and bottom."
)
