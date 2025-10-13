# ArbiterOS-Core：可靠 AI 代理的正式操作系统范式

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/badge/pypi-arbiteros--core-blue.svg)](https://pypi.org/project/arbiteros-core/)

[➡ English](README.en.md)

ArbiterOS-Core 是一个轻量级 Python 库，为构建可靠、可审计且安全的 AI 代理引入了正式的神经-符号（neuro-symbolic）操作系统范式。基于 LangGraph 构建，通过集中式策略引擎和完备可观测性提供治理能力。

## 🚀 快速开始

### 安装

```bash
pip install arbiteros-core
```

### 基本用法

```python
from arbiteros import ArbiterGraph, PolicyConfig, PolicyRule, PolicyRuleType, InstructionBinding, InstructionType
from pydantic import BaseModel

class GenerateInput(BaseModel):
    prompt: str

class GenerateOutput(BaseModel):
    text: str
    tokens_used: int

policy_config = PolicyConfig(
    policy_id="my_agent_policy",
    description="我的代理策略",
    rules=[
        PolicyRule(
            rule_id="semantic_safety_1",
            rule_type=PolicyRuleType.SEMANTIC_SAFETY,
            description="确保 GENERATE 之后必须先 VERIFY 再 TOOL_CALL",
            condition={"allowed_flows": ["GENERATE->VERIFY->TOOL_CALL"]},
            action="INTERRUPT",
            severity="critical"
        )
    ]
)

def generate_instruction(state: GenerateInput) -> dict:
    return {"text": f"生成响应：{state.prompt}", "tokens_used": len(state.prompt)}

binding = InstructionBinding(
    id="generate_1",
    instruction_type=InstructionType.GENERATE,
    input_schema=GenerateInput,
    output_schema=GenerateOutput,
    implementation=generate_instruction,
    description="基于提示生成文本"
)

arbiter_graph = ArbiterGraph(policy_config=policy_config)
arbiter_graph.add_instruction(binding)
arbiter_graph.set_entry_point("generate_1")
arbiter_graph.set_finish_point("generate_1")

result = arbiter_graph.execute({"prompt": "你好，世界！"})
print(f"结果: {result.get_state_summary()}")
```

## 🏗️ 架构

- **符号治理器（内核）**：ArbiterGraph（包装 LangGraph）、预编译策略引擎、带 OS 元数据的托管状态（debug 校验）
- **概率 CPU（LLM）**：指令绑定（契约化）、结构化输入/输出校验、模型无关执行
- **可观测性层**：飞行数据记录器、OpenTelemetry 集成、（规划）时间旅行调试

## 📋 关键特性

- **治理与安全**：语义安全、内容感知治理、资源限制、条件弹性
- **可观测性**：完整追踪、策略违规审计、延迟与成本指标
- **开发者体验**：迁移助手、交互式调试（规划）、Redis 持久化辅助

## 🎯 ACF 指令集（MVP 子集）

- 认知：GENERATE
- 记忆：COMPRESS
- 执行：TOOL_CALL
- 规范：VERIFY、CONSTRAIN、FALLBACK、INTERRUPT
- 元认知：MONITOR_RESOURCES、EVALUATE_PROGRESS、REPLAN

## 🔧 从 LangGraph 迁移

```bash
arbiteros-assist /path/to/your/langgraph/project --output-dir ./arbiteros_migration
```

## 📊 示例

- 简单代理：
```bash
python -m arbiteros.examples.simple_agent
```
- 计算器（可运行）：
```bash
python -m arbiteros.examples.simple_agent_calc --expr "(2 + 3) * 4 - 5/2"
```
- 真实演示（网页搜索 + 总结 -> 报告）：
```bash
python -m arbiteros.examples.walkthrough_demo_real --query "NVIDIA Q2 earnings"
```

## 🧪 测试

```bash
pytest
pytest --cov=arbiteros
```

## 📚 文档

- 架构指南（即将推出）
- 策略配置（即将推出）
- 迁移指南（即将推出）
- API 参考（即将推出）

## 🤝 贡献

欢迎贡献！请关注后续 CONTRIBUTING.md。

## 📄 许可证

MIT 许可证 - 详见 LICENSE。

## 🙏 致谢

- 基于 LangGraph
- 受 ArbiterOS 研究论文启发
- OpenTelemetry 集成用于可观测性
