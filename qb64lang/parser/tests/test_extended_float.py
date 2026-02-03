from ..datatypes import ExtendedFloat as EF


def test_creation():
    assert EF("1", "0").to_float() == 1.0
    assert EF("1", "2").to_float() == 100.0
    assert EF("1", "-2").to_float() == 0.01
    assert EF("-1", "1").to_float() == -10
    assert EF("-1.5", "1").to_float() == -15
    assert EF("-.5", "1").to_float() == -5
    assert EF("1.5", "1").to_float() == 15
    assert EF(".5", "-1").to_float() == 0.05
    assert EF(".5").to_float() == 0.5
    assert EF("10").to_float() == 10.0


def test_eq():
    assert EF("1", "2") == EF("1", "2")
    assert EF("-1", "2") != EF("1", "2")
    assert EF("3", "2") != EF("1", "2")
    assert EF("1", "3") != EF("1", "2")
    assert EF("1.2", "2") == EF("12", "1")
    assert EF("01.20", "2") == EF("12", "1")
    assert EF("20", "1") == EF("2", "2")


def test_lt():
    assert EF("-1", "2") < EF("1", "2")
    assert EF("1", "2") > EF("-1", "2")
    assert EF("1", "2") < EF("1", "3")
    assert EF("1", "3") > EF("1", "2")
    assert EF("1", "2") < EF("3", "2")
    assert EF("3", "2") > EF("1", "2")
    assert EF("1.1", "2") < EF("1.2", "2")
    assert EF("1.2", "2") > EF("1.1", "2")
    assert EF("1.1", "2") < EF("1.12", "2")
    assert EF("1.12", "2") > EF("1.1", "2")
    assert EF("01.10", "2") < EF("1.2", "2")


def test_neg():
    assert EF("-1", "2") > EF("-1", "3")
    assert EF("-1", "3") < EF("-1", "2")
    assert EF("-1", "2") > EF("-3", "2")
    assert EF("-3", "2") < EF("-1", "2")
    assert EF("-1.1", "2") > EF("-1.2", "2")
    assert EF("-1.2", "2") < EF("-1.1", "2")
    assert EF("-1.1", "2") > EF("-1.12", "2")
    assert EF("-1.12", "2") < EF("-1.1", "2")
    assert EF("-01.10", "2") > EF("-1.2", "2")


def test_int():
    assert int(EF("123.456")) == 123
    assert int(EF("0.5")) == 0
    assert int(EF("2", "3")) == 2000
