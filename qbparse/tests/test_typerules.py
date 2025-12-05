from qbparse import parse


def okay(input: str):
    return len(parse(input).errors) == 0


def test_assignment():
    assert okay("x = 3")
    assert okay('x$ = "foo"')
    assert not okay("x$ = 3")
    assert okay("x = 3")
