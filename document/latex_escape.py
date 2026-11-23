from __future__ import annotations

import re

LATEX_SPECIAL_CHARS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}

DANGEROUS_COMMANDS = [
    r"\\input",
    r"\\include",
    r"\\write",
    r"\\openout",
    r"\\read",
    r"\\openin",
    r"\\catcode",
    r"\\def",
    r"\\gdef",
    r"\\edef",
    r"\\xdef",
    r"\\let",
    r"\\futurelet",
    r"\\usepackage",
    r"\\RequirePackage",
    r"\\csname",
    r"\\endcsname",
    r"\\special",
    r"\\immediate",
]


def escape_latex(text: str) -> str:
    """Escapes all TeX special characters in regular text."""
    if not text:
        return ""
    # Process backslash first
    text = text.replace("\\", LATEX_SPECIAL_CHARS["\\"])
    for char, rep in LATEX_SPECIAL_CHARS.items():
        if char != "\\":
            text = text.replace(char, rep)
    return text


def sanitize_math(math_expr: str) -> str:
    """Sanitizes math formulas, blocking dangerous low-level TeX primitives."""
    for cmd in DANGEROUS_COMMANDS:
        if re.search(cmd, math_expr, re.IGNORECASE):
            math_expr = re.sub(cmd, "", math_expr, flags=re.IGNORECASE)
    return math_expr
