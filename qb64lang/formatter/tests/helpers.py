from ...parser import parse
from .. import format


def format_clean(input: str):
    program = parse(input)
    assert program.diagnostics.has_none(), program.diagnostics.diagnostics
    result = format(program)
    return result


def format_text(input: str):
    program = parse(input)
    result = format(program)
    return result
