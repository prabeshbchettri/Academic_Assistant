from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any

# Allowed operators in safe AST evaluator
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Allowed functions
SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
}


class UnsafeExpressionError(ValueError):
    pass


def safe_eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise UnsafeExpressionError(f"Unsupported binary operator: {op_type.__name__}")
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        return SAFE_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise UnsafeExpressionError(f"Unsupported unary operator: {op_type.__name__}")
        operand = safe_eval(node.operand)
        return SAFE_OPERATORS[op_type](operand)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCTIONS:
            raise UnsafeExpressionError(f"Unsupported function call: {ast.dump(node.func)}")
        func = SAFE_FUNCTIONS[node.func.id]
        args = [safe_eval(arg) for arg in node.args]
        return func(*args)
    elif isinstance(node, ast.Name):
        if node.id in SAFE_FUNCTIONS:
            return SAFE_FUNCTIONS[node.id]
        raise UnsafeExpressionError(f"Identifier not recognized: {node.id}")
    else:
        raise UnsafeExpressionError(f"Unsupported AST node: {type(node).__name__}")


def evaluate_arithmetic(expr: str) -> float | int:
    cleaned = expr.strip()
    try:
        parsed = ast.parse(cleaned, mode="eval")
        result = safe_eval(parsed)
        return result
    except Exception as exc:
        raise UnsafeExpressionError(f"Could not safely evaluate arithmetic '{expr}': {exc}") from exc


def extract_and_evaluate_formulas(text: str) -> list[dict[str, Any]]:
    """
    Finds simple mathematical statements like 'R = 10 / 2' or 'Area = 3.14 * 5**2'
    and computes the exact result deterministically.
    """
    pattern = r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9\.\s\+\-\*\/\(\)\^\%]+)"
    results = []
    for match in re.finditer(pattern, text):
        var_name = match.group(1).strip()
        expr_str = match.group(2).strip().replace("^", "**")
        try:
            val = evaluate_arithmetic(expr_str)
            results.append({"variable": var_name, "expression": expr_str, "value": val})
        except Exception:
            pass
    return results
