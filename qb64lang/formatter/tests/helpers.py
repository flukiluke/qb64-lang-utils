from ...parser import parse
from .. import format


def format_clean(input: str):
    program = parse(input)
    assert program.diagnostics.has_none()
    result = format(program)
    return result
