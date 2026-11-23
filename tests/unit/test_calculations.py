import pytest

from ai.calculations import (
    UnsafeExpressionError,
    evaluate_arithmetic,
    extract_and_evaluate_formulas,
)


def test_safe_arithmetic_evaluation():
    assert evaluate_arithmetic("10 + 25") == 35
    assert evaluate_arithmetic("100 / 4") == 25.0
    assert evaluate_arithmetic("2 ** 3") == 8
    assert evaluate_arithmetic("sqrt(16)") == 4.0
    assert evaluate_arithmetic("abs(-42)") == 42
    assert evaluate_arithmetic("round(3.14159, 2)") == 3.14


def test_blocks_unsafe_expressions():
    with pytest.raises(UnsafeExpressionError):
        evaluate_arithmetic("__import__('os').system('ls')")

    with pytest.raises(UnsafeExpressionError):
        evaluate_arithmetic("eval('2+2')")


def test_extract_and_evaluate_formulas():
    text = "In the trial, R = 100 / 5 ohms, and Area = 3.14 * 2**2 cm^2."
    formulas = extract_and_evaluate_formulas(text)
    assert len(formulas) >= 1
    names = [f["variable"] for f in formulas]
    assert "R" in names
