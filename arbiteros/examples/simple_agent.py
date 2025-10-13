"""Simple agent example demonstrating ArbiterOS capabilities."""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
import asyncio
import json

from arbiteros import ArbiterGraph, PolicyConfig, PolicyRule, PolicyRuleType, InstructionBinding, InstructionType


# Define schemas for our example
class GenerateInput(BaseModel):
	prompt: str
	max_tokens: int = 100


class GenerateOutput(BaseModel):
	text: str
	tokens_used: int


class ToolCallInput(BaseModel):
	tool_name: str
	parameters: Dict[str, Any]


class ToolCallOutput(BaseModel):
	result: Any
	success: bool


class VerifyInput(BaseModel):
	content: str
	criteria: str


class VerifyOutput(BaseModel):
	passed: bool
	confidence: float
	reasoning: str


# Add proper fallback schemas
class FallbackInput(BaseModel):
	error: str = ""
	context: Dict[str, Any] = {}


class FallbackOutput(BaseModel):
	fallback_triggered: bool
	message: str
	recovery_action: str


# Example instruction implementations
def generate_instruction(state: GenerateInput) -> Dict[str, Any]:
	"""Simple generate instruction that simulates LLM output."""
	# In a real implementation, this would call an LLM
	response = f"Generated response for: {state.prompt}"
	return {
		"text": response,
		"tokens_used": len(state.prompt) + len(response)
	}


def tool_call_instruction(state: ToolCallInput) -> Dict[str, Any]:
	"""Simple tool call instruction."""
	# Simulate tool execution
	if state.tool_name == "calculator":
		result = eval(state.parameters.get("expression", "0"))
		return {"result": result, "success": True}
	elif state.tool_name == "web_search":
		query = state.parameters.get("query", "")
		return {"result": f"Search results for: {query}", "success": True}
	else:
		return {"result": None, "success": False}


def verify_instruction(state: VerifyInput) -> Dict[str, Any]:
	"""Simple verification instruction."""
	# Simulate verification logic
	content_length = len(state.content)
	confidence = min(0.9, content_length / 100.0)  # Simple confidence calculation
	
	return {
		"passed": confidence > 0.5,
		"confidence": confidence,
		"reasoning": f"Content length: {content_length}, confidence: {confidence:.2f}"
	}


def fallback_instruction(state: FallbackInput) -> Dict[str, Any]:
	"""Fallback instruction for error recovery."""
	return {
		"fallback_triggered": True,
		"message": "Fallback mechanism activated",
		"recovery_action": "Using alternative approach"
	}


async def main():
	"""Main example demonstrating ArbiterOS capabilities."""
	
	# Create policy configuration
	policy_config = PolicyConfig(
		policy_id="simple_agent_policy",
		description="Policy for simple agent example",
		rules=[
			PolicyRule(
				rule_id="semantic_safety_1",
				rule_type=PolicyRuleType.SEMANTIC_SAFETY,
				description="Ensure GENERATE is followed by VERIFY before TOOL_CALL",
				condition={
					"allowed_flows": ["GENERATE->VERIFY->TOOL_CALL"]
				},
				action="INTERRUPT",
				severity="critical",
				applies_to=["TOOL_CALL"]
			),
			PolicyRule(
				rule_id="content_length_1",
				rule_type=PolicyRuleType.CONTENT_AWARE,
				description="Limit content length",
				condition={
					"max_length": 1000
				},
				action="FALLBACK",
				severity="warning",
				applies_to=["GENERATE"]
			),
			PolicyRule(
				rule_id="resource_limit_1",
				rule_type=PolicyRuleType.RESOURCE_LIMIT,
				description="Limit token usage",
				condition={
					"max_tokens": 500
				},
				action="INTERRUPT",
				severity="error",
				applies_to=["GENERATE", "TOOL_CALL"]
			)
		],
		max_tokens=500,
		max_execution_time=30.0,
		strict_mode=True
	)
	
	# Create instruction bindings
	generate_binding = InstructionBinding(
		id="generate_1",
		instruction_type=InstructionType.GENERATE,
		input_schema=GenerateInput,
		output_schema=GenerateOutput,
		implementation=generate_instruction,
		description="Generate text based on prompt",
		requires_verification=True,
		estimated_tokens=100
	)
	
	tool_call_binding = InstructionBinding(
		id="tool_call_1",
		instruction_type=InstructionType.TOOL_CALL,
		input_schema=ToolCallInput,
		output_schema=ToolCallOutput,
		implementation=tool_call_instruction,
		description="Execute tool call",
		requires_verification=True
	)
	
	verify_binding = InstructionBinding(
		id="verify_1",
		instruction_type=InstructionType.VERIFY,
		input_schema=VerifyInput,
		output_schema=VerifyOutput,
		implementation=verify_instruction,
		description="Verify content quality",
		estimated_tokens=50
	)
	
	fallback_binding = InstructionBinding(
		id="fallback_1",
		instruction_type=InstructionType.FALLBACK,
		input_schema=FallbackInput,
		output_schema=FallbackOutput,
		implementation=fallback_instruction,
		description="Fallback mechanism"
	)
	
	# Create ArbiterGraph
	arbiter_graph = ArbiterGraph(
		policy_config=policy_config,
		enable_observability=True
	)
	
	# Add instructions to the graph
	arbiter_graph.add_instruction(generate_binding)
	arbiter_graph.add_instruction(verify_binding)
	arbiter_graph.add_instruction(tool_call_binding)
	arbiter_graph.add_instruction(fallback_binding)
	
	# Define execution flow
	arbiter_graph.add_edge("generate_1", "verify_1")
	arbiter_graph.add_edge("verify_1", "tool_call_1")
	arbiter_graph.add_edge("tool_call_1", "fallback_1")  # Fallback path
	
	# Set entry and exit points
	arbiter_graph.set_entry_point("generate_1")
	arbiter_graph.set_finish_point("tool_call_1")
	
	# Execute the graph
	print("🚀 Starting ArbiterOS Simple Agent Example")
	print("=" * 50)
	
	try:
		# Execute with initial state
		result = arbiter_graph.execute({
			"prompt": "Calculate 2 + 2 and search for information about AI",
			"tool_name": "calculator",
			"parameters": {"expression": "2 + 2"}
		})
		
		print("✅ Execution completed successfully!")
		print(f"Final state: {json.dumps(result.get_state_summary(), indent=2)}")
		
		# Show execution trace
		trace = arbiter_graph.get_execution_trace()
		print(f"\n📊 Execution trace ({len(trace)} events):")
		for event in trace:
			print(f"  - {event.event_type}: {event.data}")
		
		# Show trace summary
		summary = arbiter_graph.get_trace_summary()
		print(f"\n📈 Trace summary:")
		print(f"  - Total events: {summary.get('total_events', 0)}")
		print(f"  - Instructions executed: {len(summary.get('instructions', []))}")
		print(f"  - Errors: {len(summary.get('errors', []))}")
		print(f"  - Policy violations: {len(summary.get('policy_violations', []))}")
		
	except Exception as e:
		print(f"❌ Execution failed: {e}")
		
		# Show error trace
		trace = arbiter_graph.get_execution_trace()
		print(f"\n🔍 Error trace ({len(trace)} events):")
		for event in trace:
			if event.event_type in ["error", "policy_violation", "fallback_triggered"]:
				print(f"  - {event.event_type}: {event.data}")


if __name__ == "__main__":
	asyncio.run(main())
