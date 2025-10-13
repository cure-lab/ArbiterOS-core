"""Simple Calculator Agent (Runnable)

This example builds a minimal governed graph that safely evaluates an
arithmetic expression and prints the result, along with an execution trace.

Run:
  python -m arbiteros.examples.simple_agent_calc --expr "(2 + 3) * 4 - 5/2"
"""

import argparse
import json
import math
import operator
import ast
from typing import Any, Dict

from pydantic import BaseModel

from arbiteros import (
	ArbiterGraph,
	PolicyConfig,
	InstructionBinding,
	InstructionType,
)

# ==========================
# Safe arithmetic evaluator
# ==========================

_ALLOWED_NODES = (
	ast.Expression,
	ast.UnaryOp,
	ast.BinOp,
	ast.Num,
	ast.Load,
	ast.Add,
	ast.Sub,
	ast.Mult,
	ast.Div,
	ast.Pow,
	ast.Mod,
	ast.USub,
	ast.UAdd,
	ast.FloorDiv,
	ast.LParen if hasattr(ast, 'LParen') else ast.AST,  # compatibility
)

_OPS = {
	ast.Add: operator.add,
	ast.Sub: operator.sub,
	ast.Mult: operator.mul,
	ast.Div: operator.truediv,
	ast.FloorDiv: operator.floordiv,
	ast.Mod: operator.mod,
	ast.Pow: operator.pow,
}


def _safe_eval_expr(node: ast.AST) -> float:
	if isinstance(node, ast.Num):
		return node.n  # type: ignore
	elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
		value = _safe_eval_expr(node.operand)
		return +value if isinstance(node.op, ast.UAdd) else -value
	elif isinstance(node, ast.BinOp) and type(node.op) in _OPS:
		left = _safe_eval_expr(node.left)
		right = _safe_eval_expr(node.right)
		return _OPS[type(node.op)](left, right)
	else:
		raise ValueError("Unsupported expression")


def safe_evaluate(expression: str) -> float:
	tree = ast.parse(expression, mode="eval")
	for n in ast.walk(tree):
		if not isinstance(n, _ALLOWED_NODES):
			raise ValueError("Invalid token in expression")
	return float(_safe_eval_expr(tree.body))


# ==========================
# Schemas & instruction impls
# ==========================

class CalcInput(BaseModel):
	expression: str


class CalcOutput(BaseModel):
	result: float


def calculator_instruction(state: CalcInput) -> Dict[str, Any]:
	value = safe_evaluate(state.expression)
	return {"result": value}


# ==========================
# Build and run graph
# ==========================

def build_graph() -> ArbiterGraph:
	policy = PolicyConfig(policy_id="calc_policy", description="Calculator policy", rules=[])
	agent = ArbiterGraph(policy_config=policy, enable_observability=True)

	calc = InstructionBinding(
		id="calc",
		instruction_type=InstructionType.TOOL_CALL,
		input_schema=CalcInput,
		output_schema=CalcOutput,
		implementation=calculator_instruction,
		description="Safely evaluate arithmetic expression",
	)

	agent.add_instruction(calc)
	agent.set_entry_point("calc")
	agent.set_finish_point("calc")
	return agent


def main() -> None:
	parser = argparse.ArgumentParser(description="Simple Calculator Agent")
	parser.add_argument("--expr", required=True, help="Arithmetic expression to evaluate")
	args = parser.parse_args()

	agent = build_graph()
	final_state = agent.execute({"expression": args.expr})

	print("\n=== Calculation Result ===")
	print(json.dumps({"expression": args.expr, "result": final_state.user_state.get("result")}, indent=2))

	print("\n=== Trace Summary ===")
	print(json.dumps(agent.get_trace_summary(), indent=2, default=str))


if __name__ == "__main__":
	main()
