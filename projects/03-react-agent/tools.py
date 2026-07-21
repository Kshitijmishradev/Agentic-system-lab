"""
Project 3 — the actual tools. Each is a plain Python function. The LLM
never executes code itself; it just names a tool + gives an input string,
and this file is what actually runs.
"""

import ast
import operator

from data import COUNTRIES

# Restricted set of operators allowed in the calculator — deliberately NOT
# using eval() on raw input, since that would let the model (or anyone
# steering it) run arbitrary code. This only understands numbers and
# +, -, *, /.
_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Disallowed expression: {ast.dump(node)}")


def calculator(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return str(result)
    except Exception as e:
        return f"error: could not evaluate '{expression}' ({e})"


def country_lookup(country_name: str) -> str:
    key = country_name.strip().lower()
    if key not in COUNTRIES:
        return f"error: no data for '{country_name}'"
    info = COUNTRIES[key]
    cities = ", ".join(f"{c.title()} (pop {p}M)" for c, p in info["cities"].items())
    return f"{country_name.title()}: GDP ${info['gdp_trillion_usd']}T. Cities: {cities}"


def city_population_lookup(city_name: str) -> str:
    key = city_name.strip().lower()
    for country, info in COUNTRIES.items():
        for city, pop in info["cities"].items():
            if city == key:
                return f"{city.title()} population: {pop} million"
    return f"error: no population data for '{city_name}'"


TOOLS = {
    "calculator": calculator,
    "country_lookup": country_lookup,
    "city_population_lookup": city_population_lookup,
}

TOOL_DESCRIPTIONS = """\
- calculator(expression): evaluate a math expression, e.g. "12.33 + 6.32"
- country_lookup(country_name): get a country's GDP and its cities with populations
- city_population_lookup(city_name): get a single city's population directly
"""
