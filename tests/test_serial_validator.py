"""Tests for the serial number validator."""
from backend.utils.serial_validator import validate_serial


def test_valid_serial_no_space():
    assert validate_serial("AD0072") == "AD0072"


def test_valid_serial_with_space():
    assert validate_serial("AD 0072") == "AD0072"


def test_lowercase_letters_normalized():
    assert validate_serial("ad0072") == "AD0072"


def test_extra_whitespace_stripped():
    assert validate_serial("  AD  0072  ") == "AD0072"


def test_three_letters_rejected():
    assert validate_serial("ASD 32") is None


def test_one_letter_rejected():
    assert validate_serial("A 1234") is None


def test_three_digits_rejected():
    assert validate_serial("AB 123") is None


def test_seven_digits_rejected():
    assert validate_serial("AB1234567") is None


def test_separators_stripped():
    # dashes / dots / slashes are recognised separators
    assert validate_serial("AB-1234") == "AB1234"
    assert validate_serial("AB_1234") == "AB1234"


def test_special_chars_rejected():
    assert validate_serial("AB#1234") is None
    assert validate_serial("AB*1234") is None


def test_empty_string_rejected():
    assert validate_serial("") is None
    assert validate_serial(None) is None  # type: ignore[arg-type]


def test_six_digits_accepted():
    assert validate_serial("AB999999") == "AB999999"


def test_four_digits_accepted():
    assert validate_serial("XY 1234") == "XY1234"
