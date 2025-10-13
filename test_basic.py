#!/usr/bin/env python3
"""Basic test for ArbiterOS-Core functionality."""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from arbiteros import (
    ArbiterGraph, 
    PolicyConfig, 
    PolicyRule, 
    PolicyRuleType, 
    InstructionBinding, 
    InstructionType
)
from pydantic import BaseModel


class TestInput(BaseModel):
    message: str


class TestOutput(BaseModel):
    result: str


def test_instruction(state: TestInput) -> dict:
    """Simple test instruction."""
    return {
        "result": f"Processed: {state.message}"
    }


def test_basic_functionality():
    """Test basic ArbiterOS functionality."""
    print("🧪 Testing ArbiterOS-Core basic functionality...")
    
    try:
        # Create policy configuration
        policy_config = PolicyConfig(
            policy_id="test_policy",
            description="Test policy",
            rules=[]
        )
        
        # Create instruction binding
        binding = InstructionBinding(
            id="test_1",
            instruction_type=InstructionType.GENERATE,
            input_schema=TestInput,
            output_schema=TestOutput,
            implementation=test_instruction,
            description="Test instruction"
        )
        
        # Create ArbiterGraph
        arbiter_graph = ArbiterGraph(policy_config=policy_config)
        arbiter_graph.add_instruction(binding)
        arbiter_graph.set_entry_point("test_1")
        arbiter_graph.set_finish_point("test_1")
        
        # Execute
        result = arbiter_graph.execute({"message": "Hello, ArbiterOS!"})
        
        print("✅ Basic functionality test passed!")
        print(f"   Result: {result.get_state_summary()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def test_policy_enforcement():
    """Test policy enforcement."""
    print("\n🧪 Testing policy enforcement...")
    
    try:
        # Create policy with rules
        policy_config = PolicyConfig(
            policy_id="test_policy_2",
            description="Test policy with rules",
            rules=[
                PolicyRule(
                    rule_id="test_rule_1",
                    rule_type=PolicyRuleType.CONTENT_AWARE,
                    description="Test content rule",
                    condition={"max_length": 100},
                    action="LOG",
                    severity="warning"
                )
            ]
        )
        
        # Create instruction binding
        binding = InstructionBinding(
            id="test_2",
            instruction_type=InstructionType.GENERATE,
            input_schema=TestInput,
            output_schema=TestOutput,
            implementation=test_instruction,
            description="Test instruction with policy"
        )
        
        # Create ArbiterGraph
        arbiter_graph = ArbiterGraph(policy_config=policy_config)
        arbiter_graph.add_instruction(binding)
        arbiter_graph.set_entry_point("test_2")
        arbiter_graph.set_finish_point("test_2")
        
        # Execute
        result = arbiter_graph.execute({"message": "Short message"})
        
        print("✅ Policy enforcement test passed!")
        print(f"   Result: {result.get_state_summary()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Policy enforcement test failed: {e}")
        return False


def test_observability():
    """Test observability features."""
    print("\n🧪 Testing observability features...")
    
    try:
        # Create policy configuration
        policy_config = PolicyConfig(
            policy_id="test_policy_3",
            description="Test policy for observability",
            rules=[]
        )
        
        # Create instruction binding
        binding = InstructionBinding(
            id="test_3",
            instruction_type=InstructionType.GENERATE,
            input_schema=TestInput,
            output_schema=TestOutput,
            implementation=test_instruction,
            description="Test instruction for observability"
        )
        
        # Create ArbiterGraph with observability
        arbiter_graph = ArbiterGraph(
            policy_config=policy_config,
            enable_observability=True
        )
        arbiter_graph.add_instruction(binding)
        arbiter_graph.set_entry_point("test_3")
        arbiter_graph.set_finish_point("test_3")
        
        # Execute
        result = arbiter_graph.execute({"message": "Observability test"})
        
        # Check observability features
        trace = arbiter_graph.get_execution_trace()
        summary = arbiter_graph.get_trace_summary()
        
        print("✅ Observability test passed!")
        print(f"   Trace events: {len(trace)}")
        print(f"   Summary: {summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ Observability test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 ArbiterOS-Core Test Suite")
    print("=" * 50)
    
    tests = [
        test_basic_functionality,
        test_policy_enforcement,
        test_observability
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! ArbiterOS-Core is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
