# ArbiterOS-Core: A Formal Operating System Paradigm for Reliable AI Agents

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/badge/pypi-arbiteros--core-blue.svg)](https://pypi.org/project/arbiteros-core/)

[➡ 中文文档 (Chinese)](README.zh.md)

ArbiterOS-Core is a lightweight Python library that introduces a formal, neuro-symbolic operating system paradigm for building reliable, auditable, and secure AI agents. Built on top of LangGraph, it provides governance capabilities through a centralized policy engine and comprehensive observability.

## 🚀 Quick Start

### Installation

```bash
pip install arbiteros-core
```

### Basic Usage

```python
from arbiteros import ArbiterGraph, PolicyConfig, PolicyRule, PolicyRuleType, InstructionBinding, InstructionType
from pydantic import BaseModel

# Define your schemas
class GenerateInput(BaseModel):
    prompt: str

class GenerateOutput(BaseModel):
    text: str
    tokens_used: int

# Create policy configuration
policy_config = PolicyConfig(
    policy_id="my_agent_policy",
    description="Policy for my agent",
    rules=[
        PolicyRule(
            rule_id="semantic_safety_1",
            rule_type=PolicyRuleType.SEMANTIC_SAFETY,
            description="Ensure GENERATE is followed by VERIFY before TOOL_CALL",
            condition={"allowed_flows": ["GENERATE->VERIFY->TOOL_CALL"]},
            action="INTERRUPT",
            severity="critical"
        )
    ]
)

# Create instruction binding
def generate_instruction(state: GenerateInput) -> dict:
    return {
        "text": f"Generated response for: {state.prompt}",
        "tokens_used": len(state.prompt)
    }

binding = InstructionBinding(
    id="generate_1",
    instruction_type=InstructionType.GENERATE,
    input_schema=GenerateInput,
    output_schema=GenerateOutput,
    implementation=generate_instruction,
    description="Generate text based on prompt"
)

# Create and execute the agent
arbiter_graph = ArbiterGraph(policy_config=policy_config)
arbiter_graph.add_instruction(binding)
arbiter_graph.set_entry_point("generate_1")
arbiter_graph.set_finish_point("generate_1")

result = arbiter_graph.execute({"prompt": "Hello, world!"})
print(f"Result: {result.get_state_summary()}")
```

## 🏗️ Architecture

ArbiterOS implements a neuro-symbolic architecture with three core components:

### 1. The Symbolic Governor (Kernel)
- **ArbiterGraph**: The central governance layer that wraps LangGraph
- **Policy Engine**: Declarative policy enforcement (precompiled rule caches)
- **Managed State**: Centralized state with OS metadata (debug validation mode)

### 2. The Probabilistic CPU (LLM)
- **Instruction Bindings**: Formal contracts for interactions
- **Schema Enforcement**: Structured input/output validation
- **Hardware Abstraction Layer**: Model-agnostic execution

### 3. The Observability Layer
- **Flight Data Recorder**: Comprehensive execution tracing
- **OpenTelemetry Integration**: Distributed tracing support
- **Time-Travel Debugging (planned)**: Step-by-step execution replay

## 📋 Key Features

- **Governance & Safety**: Semantic safety, content-aware governance, resource limits, conditional resilience
- **Observability**: Flight Data Recorder, policy violation tracking, latency & cost metrics
- **DX**: Migration assistant, interactive debugging APIs (planned), Redis checkpointer helper

## 🎯 Agent Constitution Framework (ACF)

Cores and types (MVP subset):
- Cognitive: GENERATE
- Memory: COMPRESS
- Execution: TOOL_CALL
- Normative: VERIFY, CONSTRAIN, FALLBACK, INTERRUPT
- Metacognitive: MONITOR_RESOURCES, EVALUATE_PROGRESS, REPLAN

## 🔧 Migration from LangGraph

```bash
arbiteros-assist /path/to/your/langgraph/project --output-dir ./arbiteros_migration
```

Generates ArbiterOS code, migration recommendations, and example usage.

## 📊 Examples

- Simple Agent:
```bash
python -m arbiteros.examples.simple_agent
```
- Calculator Agent (runnable):
```bash
python -m arbiteros.examples.simple_agent_calc --expr "(2 + 3) * 4 - 5/2"
```
- Real Walkthrough (web search + summary -> report):
```bash
python -m arbiteros.examples.walkthrough_demo_real --query "NVIDIA Q2 earnings"
```

## 🧪 Testing

```bash
pytest
pytest --cov=arbiteros
```

## 📚 Documentation

- Architecture Guide (coming soon)
- Policy Configuration (coming soon)
- Migration Guide (coming soon)
- API Reference (coming soon)

## 🤝 Contributing

We welcome contributions! Please see CONTRIBUTING.md (coming soon).

## 📄 License

MIT License - see LICENSE.

## 🙏 Acknowledgments

- Built on LangGraph
- Inspired by the ArbiterOS research paper
- OpenTelemetry integration for observability
