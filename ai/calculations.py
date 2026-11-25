from __future__ import annotations

import ast
import math
import operator
import re
from collections.abc import Callable
from typing import Any

SAFE_OPERATORS: dict[
    type[ast.operator] | type[ast.unaryop], Callable[..., Any]
] = {
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

SAFE_FUNCTIONS: dict[str, Any] = {
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


def safe_eval(node: ast.AST, env: dict[str, float | int] | None = None) -> Any:
    if isinstance(node, ast.Expression):
        return safe_eval(node.body, env)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise UnsafeExpressionError(f"Unsupported constant type: {type(node.value).__name__}")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise UnsafeExpressionError(f"Unsupported binary operator: {op_type.__name__}")
        left = safe_eval(node.left, env)
        right = safe_eval(node.right, env)
        if op_type is ast.Pow and isinstance(right, (int, float)) and abs(right) > 1000:
            raise UnsafeExpressionError(f"Exponent magnitude too large: {right}")
        return SAFE_OPERATORS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        unary_type = type(node.op)
        if unary_type not in SAFE_OPERATORS:
            raise UnsafeExpressionError(f"Unsupported unary operator: {unary_type.__name__}")
        operand = safe_eval(node.operand, env)
        return SAFE_OPERATORS[unary_type](operand)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCTIONS:
            raise UnsafeExpressionError(f"Unsupported function call: {ast.dump(node.func)}")
        func = SAFE_FUNCTIONS[node.func.id]
        args = [safe_eval(arg, env) for arg in node.args]
        return func(*args)
    if isinstance(node, ast.Name):
        if env and node.id in env:
            return env[node.id]
        if node.id in SAFE_FUNCTIONS:
            return SAFE_FUNCTIONS[node.id]
        raise UnsafeExpressionError(f"Identifier not recognized: {node.id}")
    raise UnsafeExpressionError(f"Unsupported AST node: {type(node).__name__}")


def evaluate_arithmetic(expr: str, env: dict[str, float | int] | None = None) -> float | int:
    cleaned = expr.strip()
    try:
        parsed = ast.parse(cleaned, mode="eval")
        result = safe_eval(parsed, env)
        if isinstance(result, float):
            return round(result, 6)
        return result
    except Exception as exc:
        raise UnsafeExpressionError(
            f"Could not safely evaluate arithmetic '{expr}': {exc}"
        ) from exc


def extract_and_evaluate_formulas(text: str) -> list[dict[str, Any]]:
    """
    Finds mathematical statements like 'R = 10 / 2 ohms' or 'I = V / R'
    and computes exact deterministic values, supporting previously assigned variables.
    """
    clauses = re.split(
        r"[,;\n]|\b(?:and|or|where|while|when|then|with|so|given)\b",
        text,
        flags=re.IGNORECASE,
    )
    pattern = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z0-9\.\s\+\-\*\/\(\)\^\%]+)")
    results: list[dict[str, Any]] = []
    env: dict[str, float | int] = {}

    for clause in clauses:
        for match in pattern.finditer(clause):
            var_name = match.group(1).strip()
            raw_expr = match.group(2).strip().rstrip(".")
            # Strip trailing unit token like 'ohms', 'V', 'cm^2', 'm/s'
            expr_clean = re.sub(
                r"(?<=[\d\)])\s+[A-Za-z]{1,8}(?:\^?-?\d+|/[A-Za-z]{1,4})?$",
                "",
                raw_expr,
            ).strip()
            expr_str = expr_clean.replace("^", "**")
            if not expr_str:
                continue
            try:
                val = evaluate_arithmetic(expr_str, env=env)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    env[var_name] = val
                    results.append(
                        {"variable": var_name, "expression": expr_str, "value": val}
                    )
            except Exception:
                pass
    return results
