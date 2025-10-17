"""Hospital Medication Delivery Robot Demo (Stage 3 - Full Robustness)

This demo showcases ArbiterOS progressive governance:
- Stage 1 (Auditability): All actions/state transitions/exceptions captured in `ManagedState` and an in-demo `audit_log`.
- Stage 2 (Resilience): Explicit `VERIFY` and `FALLBACK` instructions wired and enforced.
- Stage 3 (Full Robustness): `INTERRUPT` with simulated human-in-the-loop approval before high-risk dispense.

Run examples:
  python -m arbiteros.examples.hospital_med_delivery --scenario success
  python -m arbiteros.examples.hospital_med_delivery --scenario obstacle
  python -m arbiteros.examples.hospital_med_delivery --scenario id_mismatch
  python -m arbiteros.examples.hospital_med_delivery --scenario high_risk_denied
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict

import httpx
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
# LLM helper (optional)
# ==========================

def _openai_chat(messages: Any, max_tokens: int = 256) -> str:
    """Call OpenAI-compatible endpoint if env is configured, else return a stub.

    Env vars:
      - OPENAI_BASE_URL (e.g., https://a.fe8.cn/v1)
      - OPENAI_API_KEY (provided by user; do NOT hardcode in code)
    """
    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    if not base_url or not api_key:
        # Deterministic fallback for offline/demo
        return (
            "Plan: 1) Navigate to room; 2) Verify patient ID; 3) Risk gate; 4) Dispense or Fallback"
        )

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    with httpx.Client(timeout=30) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        # OpenAI-compatible schema
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content or "Plan: Navigate -> Verify -> RiskGate -> Dispense/Fallback"


# ==========================
# Schemas
# ==========================


class GeneratePlanInput(BaseModel):
    goal: str
    context: str = ""
    max_tokens: int = 256


class GeneratePlanOutput(BaseModel):
    plan: str
    tokens_used: int


class NavigateInput(BaseModel):
    patient_room: str
    obstacle_on_route: bool = False


class NavigateOutput(BaseModel):
    arrived: bool
    note: str


class VerifyIdentityInput(BaseModel):
    patient_id: str
    order_patient_id: str


class VerifyIdentityOutput(BaseModel):
    verified: bool
    reason: str


class RiskGateInput(BaseModel):
    high_risk: bool
    medication_name: str
    dosage: str
    simulate_approval: bool = True  # used by simulated human loop


class RiskGateOutput(BaseModel):
    approved: bool
    approver: str
    reason: str


class DispenseInput(BaseModel):
    medication_name: str
    dosage: str
    high_risk: bool
    approved: bool


class DispenseOutput(BaseModel):
    dispensed: bool
    message: str


class FallbackInput(BaseModel):
    mode: str = "safe_stop"
    context: str = ""


class FallbackOutput(BaseModel):
    action_taken: str
    details: str


# ==========================
# Helpers: human approval
# ==========================


def _human_approval_simulator(simulate_approval: bool) -> Dict[str, str | bool]:
    # In real deployments, this would reach a nurse station console with auth.
    if simulate_approval:
        return {"approved": True, "approver": "nurse.alex", "reason": "policy_ok"}
    return {"approved": False, "approver": "nurse.alex", "reason": "denied_high_risk"}


# ==========================
# Implementations
# ==========================


def impl_generate_plan(state: GeneratePlanInput) -> Dict[str, Any]:
    plan_text = _openai_chat(
        [
            {"role": "system", "content": "You are a hospital delivery robot planner."},
            {
                "role": "user",
                "content": (
                    f"Goal: {state.goal}. Provide a minimal step list using tokens: PLAN, TOOL_CALL, VERIFY, INTERRUPT, FALLBACK."
                ),
            },
        ],
        max_tokens=state.max_tokens,
    )
    return {"plan": plan_text.strip(), "tokens_used": len(plan_text)}


def impl_navigate(state: NavigateInput) -> Dict[str, Any]:
    if state.obstacle_on_route:
        note = "Obstacle detected: corridor blocked."
        return {"arrived": False, "note": note}
    return {"arrived": True, "note": f"Arrived at room {state.patient_room}"}


def impl_verify_identity(state: VerifyIdentityInput) -> Dict[str, Any]:
    ok = state.patient_id.strip() == state.order_patient_id.strip()
    reason = "match" if ok else "mismatch"
    return {"verified": ok, "reason": reason}


def impl_interrupt_risk_gate(state: RiskGateInput) -> Dict[str, Any]:
    if not state.high_risk:
        # No interrupt required
        return {"approved": True, "approver": "auto", "reason": "non_high_risk"}
    # Simulate human loop
    decision = _human_approval_simulator(state.simulate_approval)
    return {
        "approved": bool(decision.get("approved")),
        "approver": str(decision.get("approver", "unknown")),
        "reason": str(decision.get("reason", "")),
    }


def impl_dispense(state: DispenseInput) -> Dict[str, Any]:
    if state.high_risk and not state.approved:
        msg = "High-risk medication without approval; refusing to dispense."
        return {"dispensed": False, "message": msg}
    return {"dispensed": True, "message": "Medication dispensed at bedside."}


def impl_fallback(state: FallbackInput) -> Dict[str, Any]:
    details = f"Fallback engaged: {state.mode}. {state.context}".strip()
    return {"action_taken": state.mode, "details": details}


# ==========================
# Build governed graph
# ==========================


def build_policy() -> PolicyConfig:
    return PolicyConfig(
        policy_id="hospital_med_delivery",
        description="Governed flow with VERIFY, FALLBACK, and high-risk INTERRUPT",
        rules=[
            # Stage 1: auditability is implicit via ManagedState + our audit_log
            # Stage 2: encourage GENERATE->VERIFY before TOOL_CALL
            PolicyRule(
                rule_id="prefer_verify_before_actions",
                rule_type=PolicyRuleType.SEMANTIC_SAFETY,
                description="Prefer GENERATE->VERIFY before TOOL_CALL",
                condition={"allowed_flows": ["GENERATE->VERIFY->TOOL_CALL"]},
                action="LOG",
                severity="warning",
                applies_to=["TOOL_CALL"],
            ),
            # Stage 3: gating high-risk via interrupt; we log and let graph handle it explicitly
        ],
        strict_mode=False,
    )


def build_graph() -> ArbiterGraph:
    policy = build_policy()
    g = ArbiterGraph(policy_config=policy, enable_observability=True)

    gen = InstructionBinding(
        id="plan",
        instruction_type=InstructionType.GENERATE,
        input_schema=GeneratePlanInput,
        output_schema=GeneratePlanOutput,
        implementation=impl_generate_plan,
        description="Create governed plan",
        requires_verification=False,
    )

    nav = InstructionBinding(
        id="navigate",
        instruction_type=InstructionType.TOOL_CALL,
        input_schema=NavigateInput,
        output_schema=NavigateOutput,
        implementation=impl_navigate,
        description="Navigate to patient room",
        requires_verification=True,
    )

    verify = InstructionBinding(
        id="verify_identity",
        instruction_type=InstructionType.VERIFY,
        input_schema=VerifyIdentityInput,
        output_schema=VerifyIdentityOutput,
        implementation=impl_verify_identity,
        description="Verify patient identity",
    )

    risk_gate = InstructionBinding(
        id="risk_gate",
        instruction_type=InstructionType.INTERRUPT,
        input_schema=RiskGateInput,
        output_schema=RiskGateOutput,
        implementation=impl_interrupt_risk_gate,
        description="High-risk approval gate",
    )

    dispense = InstructionBinding(
        id="dispense",
        instruction_type=InstructionType.TOOL_CALL,
        input_schema=DispenseInput,
        output_schema=DispenseOutput,
        implementation=impl_dispense,
        description="Dispense medication",
    )

    fallback = InstructionBinding(
        id="fallback",
        instruction_type=InstructionType.FALLBACK,
        input_schema=FallbackInput,
        output_schema=FallbackOutput,
        implementation=impl_fallback,
        description="Fallback handler",
    )

    # Register instructions
    g.add_instruction(gen)
    g.add_instruction(nav)
    g.add_instruction(verify)
    g.add_instruction(risk_gate)
    g.add_instruction(dispense)
    g.add_instruction(fallback)

    # Flow: PLAN -> NAVIGATE -> VERIFY -> RISK_GATE -> DISPENSE
    g.add_edge("plan", "navigate")
    g.add_edge("navigate", "verify_identity")
    g.add_edge("verify_identity", "risk_gate")
    g.add_edge("risk_gate", "dispense")

    # Do not add unconditional fallback edges to avoid parallel writes.
    # The arbiter will route to `fallback` when necessary, and both
    # `dispense` and `fallback` are terminal nodes here.

    # Entry + multiple finish points
    g.set_entry_point("plan")
    g.set_finish_point("dispense")
    g.set_finish_point("fallback")
    return g


# ==========================
# Runners with sample traces
# ==========================


def run_scenario(scenario: str) -> None:
    graph = build_graph()

    # Common initial inputs
    base_inputs: Dict[str, Any] = {
        "goal": "Navigate to patient room and deliver medication",
        "audit_log": [],
        # Navigation
        "patient_room": "5A-321",
        # Identity
        "patient_id": "P-7788",
        "order_patient_id": "P-7788",
        # Medication
        "medication_name": "Heparin",
        "dosage": "5000 units",
        "high_risk": False,
        "simulate_approval": True,
    }

    if scenario == "success":
        # Non-high-risk, smooth path
        run_inputs = {**base_inputs, "obstacle_on_route": False, "high_risk": False}
    elif scenario == "obstacle":
        # Trigger obstacle fallback during navigation
        run_inputs = {**base_inputs, "obstacle_on_route": True}
    elif scenario == "id_mismatch":
        # Identity verification failure triggers fallback to alert nurse
        run_inputs = {**base_inputs, "order_patient_id": "P-9999"}
    elif scenario == "high_risk_denied":
        # High-risk requires interrupt; denial triggers fallback return
        run_inputs = {**base_inputs, "high_risk": True, "simulate_approval": False}
    else:
        raise ValueError("Unknown scenario. Choose: success|obstacle|id_mismatch|high_risk_denied")

    # Execute
    result = graph.execute(run_inputs)

    # Summaries and traces
    print("\n=== Hospital Med Delivery Demo ===")
    print(f"Scenario: {scenario}")
    print(json.dumps(result.get_state_summary(), indent=2))
    instr_hist = result.os_metadata.instruction_history if hasattr(result, "os_metadata") else []
    print("\n-- Audit Log (instruction history) --")
    for i, name in enumerate(instr_hist, 1):
        print(f"[{i}] {name}")

    # Minimal flow-only trace for clarity
    print("\n-- Flow (step names only) --")
    simple_flow = [
        "PLAN",
        "TOOL_CALL:navigate",
        "VERIFY:identity",
        "INTERRUPT:risk_gate",
        "TOOL_CALL:dispense or FALLBACK",
    ]
    print(" -> ".join(simple_flow))

    # Two example extracts
    print("\n-- Outcome --")
    if result.user_state.get("dispensed"):
        print("Success: Medication dispensed")
    else:
        fb = result.user_state.get("action_taken")
        print(f"Fallback engaged: {fb or 'N/A'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hospital Medication Delivery Robot Demo")
    parser.add_argument(
        "--scenario",
        required=True,
        help="success|obstacle|id_mismatch|high_risk_denied",
    )
    # Note for LLM config via env; not accepting secrets as args
    args = parser.parse_args()
    run_scenario(args.scenario)


if __name__ == "__main__":
    main()


