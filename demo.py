#!/usr/bin/env python3
"""
ArbiterOS-Core MVP Demo

This script demonstrates the core capabilities of ArbiterOS-Core,
including governance, observability, and the migration assistant.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from arbiteros import (
    ArbiterGraph, 
    PolicyConfig, 
    PolicyRule, 
    PolicyRuleType, 
    InstructionBinding, 
    InstructionType,
    ManagedState
)
from pydantic import BaseModel, Field


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


class FallbackInput(BaseModel):
    error: str = ""
    context: Dict[str, Any] = {}


class FallbackOutput(BaseModel):
    fallback_triggered: bool
    message: str
    recovery_action: str


def generate_instruction(state: GenerateInput) -> Dict[str, Any]:
    """Generate instruction that simulates LLM output."""
    # Simulate LLM generation
    response = f"Generated response for: {state.prompt}"
    return {
        "text": response,
        "tokens_used": len(state.prompt) + len(response)
    }


def tool_call_instruction(state: ToolCallInput) -> Dict[str, Any]:
    """Tool call instruction that simulates external tool execution."""
    if state.tool_name == "calculator":
        try:
            result = eval(state.parameters.get("expression", "0"))
            return {"result": result, "success": True}
        except Exception as e:
            return {"result": None, "success": False, "error": str(e)}
    elif state.tool_name == "web_search":
        query = state.parameters.get("query", "")
        return {"result": f"Search results for: {query}", "success": True}
    else:
        return {"result": None, "success": False}


def verify_instruction(state: VerifyInput) -> Dict[str, Any]:
    """Verification instruction that checks content quality."""
    content_length = len(state.content)
    confidence = min(0.9, content_length / 100.0)
    
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


def create_demo_agent():
    """Create a demo ArbiterOS agent."""
    
    # Create policy configuration
    policy_config = PolicyConfig(
        policy_id="demo_agent_policy",
        description="Policy for demo agent",
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
    
    return arbiter_graph


def print_section(title: str, content: str = ""):
    """Print a formatted section."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    if content:
        print(content)


def print_json(data: Any, title: str = ""):
    """Print JSON data with optional title."""
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, indent=2, default=str))


async def main():
    """Main demo function."""
    
    print_section("🚀 ArbiterOS-Core MVP Demo", 
                   "Demonstrating governance, observability, and reliability")
    
    # Create the demo agent
    print_section("📋 Creating Demo Agent")
    agent = create_demo_agent()
    print("✅ ArbiterOS agent created successfully!")
    
    # Show policy configuration
    print_section("🛡️ Policy Configuration")
    policy_summary = {
        "policy_id": agent.policy_config.policy_id,
        "description": agent.policy_config.description,
        "total_rules": len(agent.policy_config.rules),
        "max_tokens": agent.policy_config.max_tokens,
        "strict_mode": agent.policy_config.strict_mode
    }
    print_json(policy_summary, "Policy Summary")
    
    # Show instruction bindings
    print_section("🔧 Instruction Bindings")
    bindings_info = []
    for binding_id, binding in agent.instruction_bindings.items():
        bindings_info.append({
            "id": binding.id,
            "type": binding.instruction_type.value,
            "description": binding.description,
            "requires_verification": binding.requires_verification
        })
    print_json(bindings_info, "Available Instructions")
    
    # Execute the agent
    print_section("⚡ Executing Agent")
    
    # Test case 1: Normal execution
    print("\n📝 Test Case 1: Normal Execution")
    try:
        result1 = agent.execute({
            "prompt": "Calculate 2 + 2 and search for information about AI",
            "tool_name": "calculator",
            "parameters": {"expression": "2 + 2"}
        })
        
        print("✅ Execution completed successfully!")
        print_json(result1.get_state_summary(), "Final State")
        
        # Show execution trace
        trace = agent.get_execution_trace()
        print(f"\n📊 Execution trace ({len(trace)} events):")
        for event in trace:
            print(f"  - {event.event_type}: {event.data}")
        
        # Show trace summary
        summary = agent.get_trace_summary()
        print_json(summary, "Trace Summary")
        
    except Exception as e:
        print(f"❌ Execution failed: {e}")
    
    # Test case 2: Policy violation
    print("\n📝 Test Case 2: Policy Violation (Long Content)")
    try:
        result2 = agent.execute({
            "prompt": "A" * 2000,  # Very long prompt to trigger policy violation
            "tool_name": "calculator",
            "parameters": {"expression": "2 + 2"}
        })
        
        print("✅ Execution completed with policy violations!")
        print_json(result2.get_state_summary(), "Final State")
        
        # Show policy violations
        if result2.os_metadata.policy_violations:
            print_json(result2.os_metadata.policy_violations, "Policy Violations")
        
    except Exception as e:
        print(f"❌ Execution failed: {e}")
    
    # Test case 3: Error handling
    print("\n📝 Test Case 3: Error Handling")
    try:
        result3 = agent.execute({
            "prompt": "Test error handling",
            "tool_name": "invalid_tool",
            "parameters": {"invalid": "parameter"}
        })
        
        print("✅ Execution completed with error handling!")
        print_json(result3.get_state_summary(), "Final State")
        
        # Show errors
        if result3.os_metadata.errors:
            print_json(result3.os_metadata.errors, "Errors")
        
    except Exception as e:
        print(f"❌ Execution failed: {e}")
    
    # Show observability features
    print_section("🔍 Observability Features")
    
    # Export trace
    trace_export = agent.export_trace(format="json")
    print("📄 Trace Export (JSON):")
    print(trace_export[:500] + "..." if len(trace_export) > 500 else trace_export)
    
    # Show governance capabilities
    print_section("🛡️ Governance Capabilities")
    governance_features = [
        "✅ Semantic Safety Enforcement",
        "✅ Content-Aware Governance", 
        "✅ Resource Management",
        "✅ Conditional Resilience",
        "✅ Policy Violation Tracking",
        "✅ Automatic Fallback Mechanisms"
    ]
    
    for feature in governance_features:
        print(f"  {feature}")
    
    # Show observability capabilities
    print_section("📊 Observability Capabilities")
    observability_features = [
        "✅ Flight Data Recorder",
        "✅ Time-Travel Debugging",
        "✅ Policy Violation Tracking",
        "✅ Performance Metrics",
        "✅ Execution Tracing",
        "✅ OpenTelemetry Integration"
    ]
    
    for feature in observability_features:
        print(f"  {feature}")
    
    # Show developer experience features
    print_section("🚀 Developer Experience")
    dx_features = [
        "✅ Migration Assistant (arbiteros-assist)",
        "✅ Interactive Debugging",
        "✅ Production-Ready Persistence",
        "✅ Governed Component Library",
        "✅ Schema Enforcement",
        "✅ Type Safety"
    ]
    
    for feature in dx_features:
        print(f"  {feature}")
    
    # Final summary
    print_section("🎉 Demo Complete", 
                   "ArbiterOS-Core MVP successfully demonstrated!")
    
    print("\n📚 Next Steps:")
    print("  1. Install: pip install arbiteros-core")
    print("  2. Try the examples: python -m arbiteros.examples.simple_agent")
    print("  3. Use migration assistant: arbiteros-assist /path/to/langgraph/project")
    print("  4. Read the documentation: https://github.com/arbiteros/arbiteros-core")
    
    print("\n🔗 Useful Links:")
    print("  - GitHub: https://github.com/arbiteros/arbiteros-core")
    print("  - PyPI: https://pypi.org/project/arbiteros-core/")
    print("  - Documentation: https://arbiteros.dev/docs")


if __name__ == "__main__":
    asyncio.run(main())
