# ArbiterOS-Core 运行逻辑总览（中文）

本文以清晰、易懂的方式说明本项目的运行机制：各模块的功能定位、相互调用关系，以及一次典型执行从“输入到输出”的全过程。适合快速上手与内部对齐。

---

## 一图看懂：总体架构

```text
┌──────────────────────────────────────────────────────────────┐
│                        应用（Examples）                      │
│  simple_agent_calc / walkthrough_demo_real / simple_agent    │
└───────────────▲──────────────────────────────────────────────┘
                │ 传入初始 user_state / 业务输入
                │
┌───────────────┴──────────────────────────────────────────────┐
│                       ArbiterGraph（内核）                   │
│  - add_instruction / add_edge / set_entry/finish / execute   │
│  - debug 模式：每步后严格校验 ManagedState                   │
│  - 集成 FlightDataRecorder（可观测性）                        │
│  - （可选）Redis Checkpointer（持久化）                      │
└───────┬─────────────────────────────┬────────────────────────┘
        │                               │
        │ 执行 InstructionBinding       │ 调用 PolicyEngine 评估策略
        │（输入/输出模式校验 + 调用实现）│（预编译规则、O(1) 查询）
        │                               │
┌───────▼─────────────────────────────┐ ┌──────────────────────▼───────────┐
│        InstructionBinding            │ │           PolicyEngine            │
│  - instruction_type（GENERATE/…）    │ │  - 规则类型：                     │
│  - input_schema / output_schema      │ │    semantic_safety / content_…   │
│  - implementation（函数/可调用）     │ │    resource_limit / resilience   │
│  - 执行防火墙：入参/出参强校验        │ │  - 预编译缓存：applies_map/矩阵     │
└──────────────────────────────────────┘ └───────────────────────────────────┘
        │
        │ 更新
        ▼
┌──────────────────────────────────────────────────────────────┐
│                       ManagedState（状态）                    │
│  user_state（业务数据） + os_metadata（治理/统计/轨迹）       │
│  - 记录：当前指令、历史、token/时间、违规、错误、fallback…   │
└──────────────────────────────────────────────────────────────┘
        │ 产生事件
        ▼
┌──────────────────────────────────────────────────────────────┐
│                 FlightDataRecorder（飞行数据记录）           │
│  - instruction_start/end、policy_evaluation、decision 等事件 │
│  - 无 OTel 依赖时走“基础追踪”，可选接入 Jaeger/OTel           │
└──────────────────────────────────────────────────────────────┘
```

---

## 核心模块职责

- `arbiteros/core/arbiter_graph.py`（ArbiterGraph）
  - 作为“符号治理内核”，包装 LangGraph 的 StateGraph；统一添加节点/边并编译执行。
  - execute() 执行期间：
    - 逐步运行 InstructionBinding（含入/出参校验与实现调用）。
    - 每步后调用 PolicyEngine 进行策略评估（语义安全、内容、资源、弹性）。
    - 记录可观测事件到 FlightDataRecorder。
    - debug=True 时，每步严格校验 ManagedState 的结构完整性。
  - 可选：通过 `build_redis_checkpointer_from_env()` 使用 RedisSaver 持久化检查点。

- `arbiteros/core/policy_engine.py`（PolicyEngine）
  - 策略执行引擎：支持四类最小可行治理（MVG）规则：
    - 语义安全（semantic_safety）
    - 内容感知（content_aware）
    - 资源管理（resource_limit）
    - 条件弹性（conditional_resilience）
  - 预编译缓存：
    - `applies_map`：O(1) 找到适用当前 instruction_type 的规则集合。
    - `transition_matrix`：加速检查诸如 `GENERATE->TOOL_CALL` 的结构性限制/允许流。

- `arbiteros/core/instruction_binding.py`（InstructionBinding）
  - “执行防火墙 + 设备驱动”：
    - 入参：从 `ManagedState.user_state` 提取并按 `input_schema` 校验。
    - 调用实现：纯函数/可调用对象，返回字典。
    - 出参：按 `output_schema` 严格校验再回写 `user_state`。

- `arbiteros/core/managed_state.py`（ManagedState）
  - 统一的运行状态：
    - `user_state`：业务数据（输入/中间/输出）。
    - `os_metadata`：治理与统计（执行 id、当前/历史指令、tokens、耗时、错误、违规等）。

- `arbiteros/core/observability.py`（FlightDataRecorder）
  - 统一追踪：
    - 记录 `instruction_start/end`、`policy_evaluation`、`policy_violation`、`arbiter_decision` 等事件。
    - 无 OTel 环境时走基础追踪；可配置接入 Jaeger（OTel）。

- `arbiteros/components/resilient_tool_executor.py`
  - 复用子图：实现 `VERIFY -> TOOL_CALL` 的韧性执行模式（建议与语义安全策略配合）。

- `arbiteros/__init__.py`
  - 导出主要 API；提供 `build_redis_checkpointer_from_env()`，读取 `REDIS_URL` 构建 RedisSaver。

- `arbiteros/examples/*`
  - `simple_agent_calc.py`：可运行的安全算术计算器。
  - `walkthrough_demo_real.py`：真实“从搜索到报告”的四阶段演示（DuckDuckGo + Wiki 回退、压缩、评估、重规划、报告）。

---

## 运行流程（逐步）

```text
[1] 应用传入初始 user_state（如表达式、查询词等）
    │
[2] ArbiterGraph.execute():
    │  2.1 编译（可选 RedisSaver）
    │  2.2 设置 execution_id，记录 execution_start 事件
    │
[3] 执行某个 InstructionBinding 节点：
    │  3.1 FlightDataRecorder: instruction_start
    │  3.2 从 ManagedState.user_state 读取入参并按 input_schema 校验
    │  3.3 调用 implementation（具体业务逻辑/工具调用）
    │  3.4 校验 output_schema 并回写到 user_state
    │  3.5 累积 tokens / 耗时；instruction_end 事件
    │
[4] 策略评估：PolicyEngine.evaluate_rules()
    │  - 使用预编译 applies_map / transition_matrix 快速过滤和判断
    │  - 生成规则评估结果（通过/失败/动作/严重性…）并记录政策事件
    │
[5] 内核仲裁：
    │  - 严重失败 → INTERRUPT 或 FALLBACK（写入 os_metadata、记录事件）
    │  - 警告/允许 → 继续下一节点
    │
[6] debug 模式（可选）：
    │  - 每步后对 ManagedState 做严格结构校验，快速暴露集成问题
    │
[7] 结束：
    │  - 写入 execution_complete 事件
    │  - 返回最终 ManagedState，调用方可读取 user_state / trace 概要
```

---

## 调用关系（简化时序图）

### A. Calculator（simple_agent_calc）

```text
App → ArbiterGraph.execute
  → InstructionBinding(calc).execute
    → input_schema 校验（表达式）
    → calculator_instruction（安全 AST 解析 + 计算）
    → output_schema 校验（result: float）
  → PolicyEngine.evaluate_rules（无强策略，快速通过）
  → FlightDataRecorder 记录完整过程
  → 返回 ManagedState（user_state.result）
```

### B. Walkthrough（walkthrough_demo_real）

```text
App → ArbiterGraph.execute (Stage 1..4 顺次小图)
  → plan → search → verify → compress → evaluate → replan → report
  每步：
    - InstructionBinding 入/出参校验
    - implementation（如 DuckDuckGo HTML 拉取、Wiki 备选、压缩、评估、重规划、报告拼装）
    - PolicyEngine 规则评估（语义安全、内容、资源、条件弹性）
    - FlightDataRecorder 事件追踪
  → 返回报告文本（user_state.report）
```

---

## 错误处理与回退

- Implementation 抛异常：
  - 记录 error 事件，写入 os_metadata.errors；若存在 FALLBACK 指令，触发 fallback 事件与状态。
- 策略失败：
  - 严重级别（critical）→ INTERRUPT；中/低级别可 LOG 或 FALLBACK。

---

## 可观测性

- 基础追踪（默认）：无需依赖，记录关键事件到内存。
- OTel/Jaeger（可选）：安装相关依赖并设置环境变量后，可在 Jaeger UI 查看时序与治理事件。

---

## 持久化（可选）

- 设置 `REDIS_URL` 后，`build_redis_checkpointer_from_env()` 返回 RedisSaver；ArbiterGraph.compile() 使用该 Saver 实现检查点持久化。

---

## 配置与调试

- `debug=True`：启用 ManagedState 严格校验；强烈建议在开发/CI 中开启。
- `enable_observability=False`：关闭追踪输出（静默模式）。

---

## 典型输入输出示例

- Calculator：
  - 输入：`{"expression": "(2 + 3) * 4 - 5/2"}`
  - 输出：`user_state.result = 17.5`

- Walkthrough：
  - 输入：`{"query": "NVIDIA Q2 earnings"}`
  - 输出：`user_state.report = "综合搜索摘要的简要报告…"`

---

## 术语表

- InstructionBinding：对单步“指令”的契约化定义（类型、入参/出参模式、实现）。
- ManagedState：运行期统一状态，分业务数据（user_state）与治理元数据（os_metadata）。
- PolicyEngine：对每步结果进行治理评估与决策的引擎（预编译规则）。
- FlightDataRecorder：飞行数据记录器，用于可观测性与事后分析。
- Resilient Tool Executor：带 VERIFY 的韧性工具调用子图，减少外部故障对流程的影响。

---

如需进一步深入：
- 英文主文档：`README.en.md`
- 中文文档：`README.zh.md`
- 运行示例：`arbiteros/examples/*`
