"""Walkthrough Demo: Progressive Governance (Stages 1-4)

This example reproduces the illustrative walkthrough from the paper using the
current arbiteros-core framework. It builds four small graphs, one per stage,
and executes them, printing the outcomes to show brittleness -> resilience ->
context governance -> strategic oversight with replanning.

Run:
  python -m arbiteros.examples.walkthrough_demo
"""

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from arbiteros import (
    ArbiterGraph,
    PolicyConfig,
    PolicyRule,
    PolicyRuleType,
    InstructionBinding,
    InstructionType,
)

# ==========================
# Shared Schemas & Helpers
# ==========================

class GeneratePlanInput(BaseModel):
    goal: str
    max_tokens: int = 128


class GeneratePlanOutput(BaseModel):
    plan: str
    tokens_used: int


class ToolCallInput(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]


class ToolCallOutput(BaseModel):
    result: Any
    success: bool


class VerifyJsonInput(BaseModel):
    content: str
    criteria: str = "must_be_json"


class VerifyJsonOutput(BaseModel):
    passed: bool
    confidence: float
    reason: str


class CompressInput(BaseModel):
    text: str
    target_length: int = 120


class CompressOutput(BaseModel):
    summary: str
    judge_confidence: float


class EvalProgressInput(BaseModel):
    current_step: int
    progress_notes: str


class EvalProgressOutput(BaseModel):
    passed: bool
    reason: str


class ReplanInput(BaseModel):
    previous_plan: str
    issue: str


class ReplanOutput(BaseModel):
    plan: str


class FallbackInput(BaseModel):
    error: str = ""
    context: Dict[str, Any] = {}


class FallbackOutput(BaseModel):
    fallback_triggered: bool
    message: str
    recovery_action: str


# ==========================
# Implementations (no LLM)
# ==========================

def instr_generate_plan(state: GeneratePlanInput) -> Dict[str, Any]:
    # Pretend to "reason" and produce a plan
    draft = f"1) fetch_data; 2) analyze; 3) report for goal: {state.goal}"
    return {"plan": draft, "tokens_used": len(draft) + len(state.goal)}


def instr_tool_call(state: ToolCallInput) -> Dict[str, Any]:
    # Simulate an external API/tool which may fail
    if state.tool_name == "primary_fin_api":
        # Simulate intermittent 503 by parameter flag
        if state.parameters.get("force_503", False):
            # Return HTML error, i.e., a classic failure case
            return {"result": "<html>503 Service Unavailable</html>", "success": False}
        return {"result": {"sales": 12345}, "success": True}
    elif state.tool_name == "cached_backup":
        return {"result": {"sales": 12000, "cached": True}, "success": True}
    return {"result": None, "success": False}


def instr_verify_json(state: VerifyJsonInput) -> Dict[str, Any]:
    # Very naive check: content must begin with '{' and end with '}' to be JSON-like
    content = state.content.strip()
    is_json_like = content.startswith("{") and content.endswith("}")
    confidence = 0.95 if is_json_like else 0.2
    return {
        "passed": is_json_like,
        "confidence": confidence,
        "reason": "looks_like_json" if is_json_like else "not_json",
    }


def instr_compress(state: CompressInput) -> Dict[str, Any]:
    # "Summarize" by truncation, simulate judge confidence by proportion kept
    text = state.text
    if len(text) <= state.target_length:
        summary = text
    else:
        summary = text[: state.target_length] + "..."
    # Simulated LLM-as-judge confidence (higher if short enough)
    ratio = min(1.0, state.target_length / max(1, len(text)))
    judge_confidence = 0.8 + 0.2 * ratio  # 0.8..1.0 range
    return {"summary": summary, "judge_confidence": judge_confidence}


def instr_eval_progress(state: EvalProgressInput) -> Dict[str, Any]:
    # Fail if the notes mention distractions or low signal
    lower = state.progress_notes.lower()
    if "rabbit hole" in lower or "irrelevant" in lower or state.current_step > 5:
        return {"passed": False, "reason": "Unproductive path detected"}
    return {"passed": True, "reason": "On track"}


def instr_replan(state: ReplanInput) -> Dict[str, Any]:
    new_plan = f"REPLAN: 1) refocus_scope; 2) targeted_fetch; 3) concise_report | cause={state.issue}"
    return {"plan": new_plan}


def instr_fallback(state: FallbackInput) -> Dict[str, Any]:
    return {
        "fallback_triggered": True,
        "message": "Primary path failed, using backup",
        "recovery_action": "Switch to cached_backup",
    }


# ==========================
# Stage Builders
# ==========================

def build_stage1_naive() -> ArbiterGraph:
    """Stage 1: Naive brittle sequence: GENERATE -> TOOL_CALL (primary) -> REPORT.
    Demonstrates failure when the primary tool fails (503-like)."""
    policy = PolicyConfig(policy_id="stage1", description="Naive brittle flow", rules=[])
    g = ArbiterGraph(policy_config=policy, enable_observability=True)

    gen = InstructionBinding(
        id="generate_plan",
        instruction_type=InstructionType.GENERATE,
        input_schema=GeneratePlanInput,
        output_schema=GeneratePlanOutput,
        implementation=instr_generate_plan,
        description="Generate initial plan",
        requires_verification=False,
    )

    call = InstructionBinding(
        id="call_primary",
        instruction_type=InstructionType.TOOL_CALL,
        input_schema=ToolCallInput,
        output_schema=ToolCallOutput,
        implementation=instr_tool_call,
        description="Call primary financial API",
        requires_verification=False,
    )

    g.add_instruction(gen)
    g.add_instruction(call)
    g.add_edge("generate_plan", "call_primary")
    g.set_entry_point("generate_plan")
    g.set_finish_point("call_primary")
    return g


def build_stage2_resilient() -> ArbiterGraph:
    """Stage 2: Add VERIFY and FALLBACK. If VERIFY fails, still proceed and later use
    a backup tool. For simplicity, we call primary then backup unconditionally to
    demonstrate resilience (in a production graph we'd use conditional edges)."""
    rules: List[PolicyRule] = [
        PolicyRule(
            rule_id="require_json_before_tool",
            rule_type=PolicyRuleType.SEMANTIC_SAFETY,
            description="Encourage think-then-verify before high-stakes tool",
            condition={"allowed_flows": ["GENERATE->VERIFY->TOOL_CALL"]},
            action="LOG",
            severity="warning",
            applies_to=["TOOL_CALL"],
        )
    ]
    policy = PolicyConfig(policy_id="stage2", description="VERIFY + FALLBACK", rules=rules)
    g = ArbiterGraph(policy_config=policy, enable_observability=True)

    gen = InstructionBinding(
        id="generate_plan",
        instruction_type=InstructionType.GENERATE,
        input_schema=GeneratePlanInput,
        output_schema=GeneratePlanOutput,
        implementation=instr_generate_plan,
        description="Generate initial plan",
        requires_verification=False,
    )

    verify = InstructionBinding(
        id="verify_json",
        instruction_type=InstructionType.VERIFY,
        input_schema=VerifyJsonInput,
        output_schema=VerifyJsonOutput,
        implementation=instr_verify_json,
        description="Verify primary API response is JSON",
    )

    call_primary = InstructionBinding(
        id="call_primary",
        instruction_type=InstructionType.TOOL_CALL,
        input_schema=ToolCallInput,
        output_schema=ToolCallOutput,
        implementation=instr_tool_call,
        description="Call primary financial API",
    )

    call_backup = InstructionBinding(
        id="call_backup",
        instruction_type=InstructionType.TOOL_CALL,
        input_schema=ToolCallInput,
        output_schema=ToolCallOutput,
        implementation=instr_tool_call,
        description="Call cached backup source",
    )

    fallback = InstructionBinding(
        id="fallback",
        instruction_type=InstructionType.FALLBACK,
        input_schema=FallbackInput,
        output_schema=FallbackOutput,
        implementation=instr_fallback,
        description="Fallback mechanism",
    )

    g.add_instruction(gen)
    g.add_instruction(verify)
    g.add_instruction(call_primary)
    g.add_instruction(call_backup)
    g.add_instruction(fallback)

    # Linear flow to demonstrate verification and fallback presence
    g.add_edge("generate_plan", "verify_json")
    g.add_edge("verify_json", "call_primary")
    g.add_edge("call_primary", "fallback")   # in demo we'll show fallback action
    g.add_edge("fallback", "call_backup")     # then backup

    g.set_entry_point("generate_plan")
    g.set_finish_point("call_backup")
    return g


def build_stage3_memory_governance() -> ArbiterGraph:
    """Stage 3: Add COMPRESS + probabilistic judge confidence.
    We will simulate confidence and continue."""
    policy = PolicyConfig(policy_id="stage3", description="COMPRESS with judge", rules=[])
    g = ArbiterGraph(policy_config=policy, enable_observability=True)

    gen = InstructionBinding(
        id="generate_plan",
        instruction_type=InstructionType.GENERATE,
        input_schema=GeneratePlanInput,
        output_schema=GeneratePlanOutput,
        implementation=instr_generate_plan,
        description="Generate initial plan",
    )

    compress = InstructionBinding(
        id="compress_notes",
        instruction_type=InstructionType.COMPRESS,
        input_schema=CompressInput,
        output_schema=CompressOutput,
        implementation=instr_compress,
        description="Summarize gathered info with judged confidence",
    )

    call_primary = InstructionBinding(
        id="call_primary",
        instruction_type=InstructionType.TOOL_CALL,
        input_schema=ToolCallInput,
        output_schema=ToolCallOutput,
        implementation=instr_tool_call,
        description="Call primary financial API",
    )

    g.add_instruction(gen)
    g.add_instruction(compress)
    g.add_instruction(call_primary)

    g.add_edge("generate_plan", "compress_notes")
    g.add_edge("compress_notes", "call_primary")

    g.set_entry_point("generate_plan")
    g.set_finish_point("call_primary")
    return g


def build_stage4_metacognitive_replan() -> ArbiterGraph:
    """Stage 4: Add EVALUATE_PROGRESS -> REPLAN.
    We demonstrate detecting an unproductive path and then replanning."""
    policy = PolicyConfig(policy_id="stage4", description="Evaluate & Replan", rules=[])
    g = ArbiterGraph(policy_config=policy, enable_observability=True)

    gen = InstructionBinding(
        id="generate_plan",
        instruction_type=InstructionType.GENERATE,
        input_schema=GeneratePlanInput,
        output_schema=GeneratePlanOutput,
        implementation=instr_generate_plan,
        description="Generate initial plan",
    )

    evalp = InstructionBinding(
        id="evaluate_progress",
        instruction_type=InstructionType.EVALUATE_PROGRESS,
        input_schema=EvalProgressInput,
        output_schema=EvalProgressOutput,
        implementation=instr_eval_progress,
        description="Detect rabbit-holes and low-signal paths",
    )

    replan = InstructionBinding(
        id="replan",
        instruction_type=InstructionType.REPLAN,
        input_schema=ReplanInput,
        output_schema=ReplanOutput,
        implementation=instr_replan,
        description="Strategic replan",
    )

    call_primary = InstructionBinding(
        id="call_primary",
        instruction_type=InstructionType.TOOL_CALL,
        input_schema=ToolCallInput,
        output_schema=ToolCallOutput,
        implementation=instr_tool_call,
        description="Call primary financial API",
    )

    g.add_instruction(gen)
    g.add_instruction(evalp)
    g.add_instruction(replan)
    g.add_instruction(call_primary)

    # For demonstration, always go through EVALUATE -> REPLAN -> TOOL
    g.add_edge("generate_plan", "evaluate_progress")
    g.add_edge("evaluate_progress", "replan")
    g.add_edge("replan", "call_primary")

    g.set_entry_point("generate_plan")
    g.set_finish_point("call_primary")
    return g


# ==========================
# Execution Utilities
# ==========================

def run_stage(title: str, graph: ArbiterGraph, initial_state: Dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

    result = graph.execute(initial_state)

    print("Final State Summary:")
    print(json.dumps(result.get_state_summary(), indent=2))

    trace_summary = graph.get_trace_summary()
    print("\nTrace Summary:")
    print(json.dumps(trace_summary, indent=2, default=str))


def main() -> None:
    # Stage 1: Naive brittle flow - primary tool fails (force_503)
    stage1 = build_stage1_naive()
    run_stage(
        "Stage 1: Naive Prototype (Brittle Execution)",
        stage1,
        {
            "goal": "market analysis report",
            "tool_name": "primary_fin_api",
            "parameters": {"force_503": True},  # simulate 503 failure
        },
    )

    # Stage 2: Add VERIFY + FALLBACK -> backup source
    stage2 = build_stage2_resilient()
    # For demo simplicity, we pass the "content" to verify_json as what generate/tool produced next
    run_stage(
        "Stage 2: Resilience via VERIFY + FALLBACK",
        stage2,
        {
            "goal": "market analysis report",
            # simulate that verify will fail if content isn't JSON; we keep flow linear
            "content": "<html>503 Service Unavailable</html>",
            "tool_name": "primary_fin_api",
            "parameters": {"force_503": True},
        },
    )

    # Stage 3: Governed memory (COMPRESS + judged confidence)
    stage3 = build_stage3_memory_governance()
    run_stage(
        "Stage 3: Governing Context (COMPRESS with LLM-as-judge)",
        stage3,
        {
            "goal": "market analysis report",
            "text": (
                "Long notes: sales figures Q1..Q4; market news about competitors; "
                "macro indicators; more details and elaborations..."
            ),
            "target_length": 80,
            "tool_name": "primary_fin_api",
            "parameters": {"force_503": False},
        },
    )

    # Stage 4: Metacognitive oversight (EVALUATE_PROGRESS -> REPLAN)
    stage4 = build_stage4_metacognitive_replan()
    run_stage(
        "Stage 4: Strategic Oversight (EVALUATE_PROGRESS -> REPLAN)",
        stage4,
        {
            "goal": "market analysis report",
            "current_step": 6,  # high step count to trigger fail
            "progress_notes": "Went down a rabbit hole with irrelevant news",
            "previous_plan": "1) broad_web_search; 2) summarize; 3) finalize",
            "issue": "Unproductive reasoning path",
            "tool_name": "primary_fin_api",
            "parameters": {"force_503": False},
        },
    )


if __name__ == "__main__":
    main()
