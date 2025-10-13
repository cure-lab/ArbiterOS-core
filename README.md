# ArbiterOS-Core: A Formal Operating System Paradigm for Reliable AI Agents

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/badge/pypi-arbiteros--core-blue.svg)](https://pypi.org/project/arbiteros-core/)

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
- **Policy Engine**: Declarative policy enforcement
- **Managed State**: Centralized state management with OS metadata

### 2. The Probabilistic CPU (LLM)
- **Instruction Bindings**: Formal contracts for LLM interactions
- **Schema Enforcement**: Structured input/output validation
- **Hardware Abstraction Layer**: Model-agnostic execution

### 3. The Observability Layer
- **Flight Data Recorder**: Comprehensive execution tracing
- **OpenTelemetry Integration**: Distributed tracing support
- **Time-Travel Debugging**: Step-by-step execution replay

## 📋 Key Features

### 🛡️ Governance & Safety
- **Semantic Safety**: Enforce "think then verify" workflows
- **Content-Aware Governance**: Rules based on content analysis
- **Resource Management**: Token and time limits
- **Conditional Resilience**: Automatic fallback mechanisms

### 🔍 Observability & Debugging
- **Flight Data Recorder**: Complete execution traces
- **Time-Travel Debugging**: Replay any execution step
- **Policy Violation Tracking**: Audit trail of governance decisions
- **Performance Metrics**: Latency and cost tracking

### 🚀 Developer Experience
- **Migration Assistant**: Convert LangGraph projects to ArbiterOS
- **Interactive Debugging**: Human-in-the-loop workflows
- **Production-Ready Persistence**: Redis checkpointing
- **Governed Component Library**: Pre-built, reliable components

## 🎯 Agent Constitution Framework (ACF)

ArbiterOS organizes instructions into five cores:

- **Cognitive Core**: Internal reasoning (GENERATE, REFLECT)
- **Memory Core**: Context management (COMPRESS, FILTER, LOAD)
- **Execution Core**: External interactions (TOOL_CALL)
- **Normative Core**: Safety and verification (VERIFY, CONSTRAIN, FALLBACK, INTERRUPT)
- **Metacognitive Core**: Strategic oversight (MONITOR_RESOURCES, EVALUATE_PROGRESS, REPLAN)

## 🔧 Migration from LangGraph

Use the migration assistant to convert existing LangGraph projects:

```bash
arbiteros-assist /path/to/your/langgraph/project --output-dir ./arbiteros_migration
```

This will:
- Analyze your LangGraph project
- Generate ArbiterOS code
- Provide migration recommendations
- Create example usage files

## 📊 Examples

### Simple Agent
```python
# See examples/simple_agent.py for a complete example
python -m arbiteros.examples.simple_agent
```

### Migration Assistant
```python
# See examples/migration_example.py for migration examples
python -m arbiteros.examples.migration_example
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=arbiteros

# Run specific test categories
pytest -m "not slow"
```

## 📚 Documentation

- [Architecture Guide](docs/architecture.md)
- [Policy Configuration](docs/policies.md)
- [Migration Guide](docs/migration.md)
- [API Reference](docs/api.md)

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on [LangGraph](https://github.com/langchain-ai/langgraph)
- Inspired by the ArbiterOS research paper
- OpenTelemetry integration for observability

---

# ArbiterOS-Core: 可靠AI代理的正式操作系统范式

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/badge/pypi-arbiteros--core-blue.svg)](https://pypi.org/project/arbiteros-core/)

ArbiterOS-Core 是一个轻量级Python库，为构建可靠、可审计和安全的AI代理引入了正式的神经符号操作系统范式。基于LangGraph构建，通过集中式策略引擎和全面的可观测性提供治理能力。

## 🚀 快速开始

### 安装

```bash
pip install arbiteros-core
```

### 基本用法

```python
from arbiteros import ArbiterGraph, PolicyConfig, PolicyRule, PolicyRuleType, InstructionBinding, InstructionType
from pydantic import BaseModel

# 定义你的模式
class GenerateInput(BaseModel):
    prompt: str

class GenerateOutput(BaseModel):
    text: str
    tokens_used: int

# 创建策略配置
policy_config = PolicyConfig(
    policy_id="my_agent_policy",
    description="我的代理策略",
    rules=[
        PolicyRule(
            rule_id="semantic_safety_1",
            rule_type=PolicyRuleType.SEMANTIC_SAFETY,
            description="确保GENERATE后跟VERIFY再执行TOOL_CALL",
            condition={"allowed_flows": ["GENERATE->VERIFY->TOOL_CALL"]},
            action="INTERRUPT",
            severity="critical"
        )
    ]
)

# 创建指令绑定
def generate_instruction(state: GenerateInput) -> dict:
    return {
        "text": f"为以下内容生成响应: {state.prompt}",
        "tokens_used": len(state.prompt)
    }

binding = InstructionBinding(
    id="generate_1",
    instruction_type=InstructionType.GENERATE,
    input_schema=GenerateInput,
    output_schema=GenerateOutput,
    implementation=generate_instruction,
    description="基于提示生成文本"
)

# 创建并执行代理
arbiter_graph = ArbiterGraph(policy_config=policy_config)
arbiter_graph.add_instruction(binding)
arbiter_graph.set_entry_point("generate_1")
arbiter_graph.set_finish_point("generate_1")

result = arbiter_graph.execute({"prompt": "你好，世界！"})
print(f"结果: {result.get_state_summary()}")
```

## 🏗️ 架构

ArbiterOS实现了具有三个核心组件的神经符号架构：

### 1. 符号治理器（内核）
- **ArbiterGraph**: 包装LangGraph的中央治理层
- **策略引擎**: 声明式策略执行
- **托管状态**: 带有OS元数据的集中式状态管理

### 2. 概率CPU（LLM）
- **指令绑定**: LLM交互的正式合约
- **模式执行**: 结构化输入/输出验证
- **硬件抽象层**: 模型无关的执行

### 3. 可观测性层
- **飞行数据记录器**: 全面的执行跟踪
- **OpenTelemetry集成**: 分布式跟踪支持
- **时间旅行调试**: 逐步执行重放

## 📋 主要特性

### 🛡️ 治理与安全
- **语义安全**: 执行"思考然后验证"工作流
- **内容感知治理**: 基于内容分析的规则
- **资源管理**: Token和时间限制
- **条件弹性**: 自动回退机制

### 🔍 可观测性与调试
- **飞行数据记录器**: 完整的执行跟踪
- **时间旅行调试**: 重放任何执行步骤
- **策略违规跟踪**: 治理决策的审计跟踪
- **性能指标**: 延迟和成本跟踪

### 🚀 开发者体验
- **迁移助手**: 将LangGraph项目转换为ArbiterOS
- **交互式调试**: 人在回路工作流
- **生产就绪持久化**: Redis检查点
- **治理组件库**: 预构建的可靠组件

## 🎯 代理宪法框架（ACF）

ArbiterOS将指令组织为五个核心：

- **认知核心**: 内部推理（GENERATE, REFLECT）
- **记忆核心**: 上下文管理（COMPRESS, FILTER, LOAD）
- **执行核心**: 外部交互（TOOL_CALL）
- **规范核心**: 安全和验证（VERIFY, CONSTRAIN, FALLBACK, INTERRUPT）
- **元认知核心**: 战略监督（MONITOR_RESOURCES, EVALUATE_PROGRESS, REPLAN）

## 🔧 从LangGraph迁移

使用迁移助手转换现有的LangGraph项目：

```bash
arbiteros-assist /path/to/your/langgraph/project --output-dir ./arbiteros_migration
```

这将：
- 分析你的LangGraph项目
- 生成ArbiterOS代码
- 提供迁移建议
- 创建示例用法文件

## 📊 示例

### 简单代理
```python
# 查看 examples/simple_agent.py 获取完整示例
python -m arbiteros.examples.simple_agent
```

### 迁移助手
```python
# 查看 examples/migration_example.py 获取迁移示例
python -m arbiteros.examples.migration_example
```

## 🧪 测试

```bash
# 运行测试
pytest

# 运行覆盖率测试
pytest --cov=arbiteros

# 运行特定测试类别
pytest -m "not slow"
```

## 📚 文档

- [架构指南](docs/architecture.md)
- [策略配置](docs/policies.md)
- [迁移指南](docs/migration.md)
- [API参考](docs/api.md)

## 🤝 贡献

我们欢迎贡献！请查看[CONTRIBUTING.md](CONTRIBUTING.md)了解指南。

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情。

## 🙏 致谢

- 基于[LangGraph](https://github.com/langchain-ai/langgraph)构建
- 受ArbiterOS研究论文启发
- OpenTelemetry集成用于可观测性
