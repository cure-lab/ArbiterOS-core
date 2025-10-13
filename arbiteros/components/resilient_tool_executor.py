"""Resilient Tool Executor component

A reusable governed subgraph pattern:
  PLAN/INPUT -> VERIFY -> TOOL_CALL, with descriptive bindings and suggested policies.
This is a lightweight, copy-pastable component to speed up adoption.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from arbiteros import (
	ArbiterGraph,
	PolicyConfig,
	PolicyRule,
	PolicyRuleType,
	InstructionBinding,
	InstructionType,
)


class VerifyInput(BaseModel):
	content: str
	criteria: str = "signal"


class VerifyOutput(BaseModel):
	passed: bool
	confidence: float
	reason: str


class ToolInput(BaseModel):
	tool_name: str
	parameters: Dict[str, Any]


class ToolOutput(BaseModel):
	result: Any
	success: bool


def default_verify_impl(state: VerifyInput) -> Dict[str, Any]:
	ok = len(state.content.strip()) > 30
	conf = 0.9 if ok else 0.4
	return {"passed": ok, "confidence": conf, "reason": "ok" if ok else "low_signal"}


def build_resilient_executor(
	verify_impl=default_verify_impl,
	tool_impl=None,
	policy_id: str = "resilient_executor_policy",
	description: str = "Resilient executor with VERIFY -> TOOL_CALL",
) -> ArbiterGraph:
	"""Create a small ArbiterGraph that enforces VERIFY -> TOOL_CALL pattern.
	Caller must provide `tool_impl` (callable) for the TOOL_CALL step.
	"""
	if tool_impl is None:
		raise ValueError("tool_impl is required")

	rules: List[PolicyRule] = [
		PolicyRule(
			rule_id="require_verify_before_tool",
			rule_type=PolicyRuleType.SEMANTIC_SAFETY,
			description="Encourage GENERATE/VERIFY before TOOL_CALL",
			condition={"allowed_flows": ["GENERATE->VERIFY->TOOL_CALL", "VERIFY->TOOL_CALL"]},
			action="LOG",
			severity="warning",
			applies_to=["TOOL_CALL"],
		)
	]
	policy = PolicyConfig(policy_id=policy_id, description=description, rules=rules)
	ag = ArbiterGraph(policy_config=policy, enable_observability=True)

	verify = InstructionBinding(
		id="verify",
		instruction_type=InstructionType.VERIFY,
		input_schema=VerifyInput,
		output_schema=VerifyOutput,
		implementation=verify_impl,
		description="Verify content signal",
	)

	tool = InstructionBinding(
		id="tool",
		instruction_type=InstructionType.TOOL_CALL,
		input_schema=ToolInput,
		output_schema=ToolOutput,
		implementation=tool_impl,
		description="Execute tool",
	)

	ag.add_instruction(verify)
	ag.add_instruction(tool)
	ag.add_edge("verify", "tool")
	ag.set_entry_point("verify")
	ag.set_finish_point("tool")
	return ag
