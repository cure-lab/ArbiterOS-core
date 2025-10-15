"""Real Walkthrough Demo (Runnable)

This demo implements the 4-stage progressive governance walkthrough with
actual web fetching and summarization to produce a brief report.

Web search is implemented via DuckDuckGo HTML (no API key required) and
optionally falls back to Wikipedia page extracts if needed.

Run:
  python -m arbiteros.examples.walkthrough_demo_real --query "NVIDIA Q2 earnings"
"""

import argparse
import json
import re
from typing import Any, Dict, List

import httpx
from pydantic import BaseModel

from arbiteros import (
	ArbiterGraph,
	PolicyConfig,
	PolicyRule,
	PolicyRuleType,
	InstructionBinding,
	InstructionType,
)

# ==========================
# Simple web utilities (synchronous)
# ==========================

DUCK_URL = "https://duckduckgo.com/html/"
DUCK_URL_ALT = "https://r.jina.ai/http://duckduckgo.com/html/"  # via jina mirror (read-only fetch)
DUCK_INSTANT_API = "https://api.duckduckgo.com/"
WIKI_SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WIKI_PAGE_TEXT = "https://r.jina.ai/http://en.wikipedia.org/wiki/{}"  # read-only text proxy


def _client() -> httpx.Client:
	return httpx.Client(timeout=20, headers={
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
			"(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
	})


def fetch_duckduckgo(query: str) -> str:
	params = {"q": query}
	with _client() as client:
		r = client.get(DUCK_URL, params=params)
		r.raise_for_status()
		return r.text


def fetch_duckduckgo_alt(query: str) -> str:
	# Read-only fetch through r.jina.ai mirror, useful when direct access fails
	params = {"q": query}
	with _client() as client:
		r = client.get(DUCK_URL_ALT, params=params)
		r.raise_for_status()
		return r.text


def fetch_duckduckgo_instant(query: str) -> str:
	# DuckDuckGo Instant Answer API (no key). Returns concise abstract + related topics.
	params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
	with httpx.Client(timeout=15, headers={"User-Agent": "Mozilla/5.0"}) as client:
		r = client.get(DUCK_INSTANT_API, params=params)
		r.raise_for_status()
		data = r.json()
		abstract = (data.get("AbstractText") or "").strip()
		related = []
		for t in data.get("RelatedTopics", [])[:5]:
			text = t.get("Text") if isinstance(t, dict) else None
			if text:
				related.append(text)
		text_parts = [p for p in [abstract, "\n".join(related)] if p]
		return "\n".join(text_parts)


def extract_snippets_from_duck(html: str, limit: int = 5) -> List[str]:
	snippets: List[str] = []
	for m in re.finditer(r"<a.*?class=\"result__a.*?>(.*?)</a>.*?<a.*?result__snippet.*?>(.*?)</a>", html, re.S):
		title = re.sub("<.*?>", "", m.group(1))
		snippet = re.sub("<.*?>", "", m.group(2))
		text = f"{title} - {snippet}"
		snippets.append(re.sub(r"\s+", " ", text).strip())
		if len(snippets) >= limit:
			break
	# 兜底：若选择器失效，退化为提取 <a ... result__a> 的标题
	if not snippets:
		for m in re.finditer(r"<a[^>]*class=\"result__a[^\"]*\"[^>]*>(.*?)</a>", html, re.S):
			title = re.sub("<.*?>", "", m.group(1))
			if title:
				snippets.append(title.strip())
				if len(snippets) >= limit:
					break
	return snippets


def fetch_wikipedia_summary(topic: str) -> str:
	slug = topic.strip().replace(" ", "_")
	url = WIKI_SUMMARY_API.format(slug)
	with _client() as client:
		r = client.get(url)
		if r.status_code == 200:
			data = r.json()
			return data.get("extract", "")
	return ""


def fetch_wikipedia_page_text(topic: str) -> str:
	slug = topic.strip().replace(" ", "_")
	url = WIKI_PAGE_TEXT.format(slug)
	with httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"}) as client:
		r = client.get(url)
		if r.status_code == 200:
			text = r.text
			# r.jina.ai 返回的已是可读文本，不需要复杂清洗；简单裁剪
			return text.strip()
	return ""


# ==========================
# Schemas
# ==========================

class PlanInput(BaseModel):
	query: str


class PlanOutput(BaseModel):
	plan: str
	tokens_used: int


class SearchInput(BaseModel):
	query: str
	force_fail: bool = False


class SearchOutput(BaseModel):
	text: str
	success: bool


class VerifyInput(BaseModel):
	content: str
	criteria: str


class VerifyOutput(BaseModel):
	passed: bool
	confidence: float
	reason: str


class CompressInput(BaseModel):
	text: str
	target_length: int = 600


class CompressOutput(BaseModel):
	summary: str
	judge_confidence: float


class EvalInput(BaseModel):
	notes: str
	step: int


class EvalOutput(BaseModel):
	passed: bool
	reason: str


class ReplanInput(BaseModel):
	plan: str
	issue: str


class ReplanOutput(BaseModel):
	plan: str


class ReportInput(BaseModel):
	summary: str
	query: str


class ReportOutput(BaseModel):
	report: str


# ==========================
# Implementations (synchronous)
# ==========================

def impl_plan(state: PlanInput) -> Dict[str, Any]:
	plan = "1) web_search; 2) verify_signal; 3) compress_notes; 4) report"
	return {"plan": plan, "tokens_used": len(plan) + len(state.query)}


def _best_effort_search_text(query: str) -> str:
	# 尝试顺序：DDG Instant → DDG HTML → DDG（jina 代理）→ Wikipedia 摘要 → Wikipedia 页面文本 → 兜底提示
	try:
		ia = fetch_duckduckgo_instant(query)
		if ia and len(ia.strip()) > 0:
			return ia
	except Exception:
		pass
	try:
		html = fetch_duckduckgo(query)
		snips = extract_snippets_from_duck(html, 5)
		if snips:
			return "\n".join(snips)
	except Exception:
		pass
	try:
		html2 = fetch_duckduckgo_alt(query)
		snips2 = extract_snippets_from_duck(html2, 5)
		if snips2:
			return "\n".join(snips2)
	except Exception:
		pass
	wiki = fetch_wikipedia_summary(query)
	if wiki:
		return wiki
	page_text = fetch_wikipedia_page_text(query)
	if page_text:
		return page_text[:1000] + ("..." if len(page_text) > 1000 else "")
	return "No public summary available. Please check network or try another query."


def impl_search(state: SearchInput) -> Dict[str, Any]:
	text = _best_effort_search_text(state.query)
	return {"text": text, "success": text != "" and not text.startswith("No public summary")}


def impl_verify(state: VerifyInput) -> Dict[str, Any]:
	content = state.content.strip()
	ok = len(content) > 40  # crude signal threshold
	conf = 0.9 if ok else 0.3
	return {"passed": ok, "confidence": conf, "reason": "enough_signal" if ok else "low_signal"}


def impl_compress(state: CompressInput) -> Dict[str, Any]:
	text = state.text
	if len(text) <= state.target_length:
		summary = text
	else:
		summary = text[: state.target_length] + "..."
	ratio = min(1.0, state.target_length / max(1, len(text)))
	judge_confidence = 0.8 + 0.2 * ratio
	return {"summary": summary, "judge_confidence": judge_confidence}


def impl_eval(state: EvalInput) -> Dict[str, Any]:
	bad = any(k in state.notes.lower() for k in ["rabbit hole", "irrelevant", "off-topic"]) or state.step > 6
	return {"passed": not bad, "reason": "on_track" if not bad else "need_replan"}


def impl_replan(state: ReplanInput) -> Dict[str, Any]:
	new_plan = "1) focused_web_search; 2) compress; 3) report"
	return {"plan": new_plan}


def impl_report(state: ReportInput) -> Dict[str, Any]:
	report = f"Report for query '{state.query}':\n\n{state.summary}\n\n-- End of report --"
	return {"report": report}


# ==========================
# Build per-stage graphs
# ==========================

def build_stage1(query: str) -> ArbiterGraph:
	policy = PolicyConfig(policy_id="stage1", description="Naive brittle", rules=[])
	ag = ArbiterGraph(policy_config=policy, enable_observability=True)

	plan = InstructionBinding(
		id="plan",
		instruction_type=InstructionType.GENERATE,
		input_schema=PlanInput,
		output_schema=PlanOutput,
		implementation=impl_plan,
		description="Make naive plan",
	)

	search = InstructionBinding(
		id="search",
		instruction_type=InstructionType.TOOL_CALL,
		input_schema=SearchInput,
		output_schema=SearchOutput,
		implementation=impl_search,
		description="Web search (may fail)",
	)

	ag.add_instruction(plan)
	ag.add_instruction(search)
	ag.add_edge("plan", "search")
	ag.set_entry_point("plan")
	ag.set_finish_point("search")
	return ag


def build_stage2(query: str) -> ArbiterGraph:
	rules = [
		PolicyRule(
			rule_id="think_then_verify",
			rule_type=PolicyRuleType.SEMANTIC_SAFETY,
			description="Prefer GENERATE->VERIFY before TOOL_CALL",
			condition={"allowed_flows": ["GENERATE->VERIFY->TOOL_CALL"]},
			action="LOG",
			severity="warning",
			applies_to=["TOOL_CALL"],
		)
	]
	policy = PolicyConfig(policy_id="stage2", description="VERIFY + fallback", rules=rules)
	ag = ArbiterGraph(policy_config=policy, enable_observability=True)

	plan = InstructionBinding(
		id="plan",
		instruction_type=InstructionType.GENERATE,
		input_schema=PlanInput,
		output_schema=PlanOutput,
		implementation=impl_plan,
		description="Plan",
	)

	verify = InstructionBinding(
		id="verify",
		instruction_type=InstructionType.VERIFY,
		input_schema=VerifyInput,
		output_schema=VerifyOutput,
		implementation=impl_verify,
		description="Verify content signal",
	)

	search = InstructionBinding(
		id="search",
		instruction_type=InstructionType.TOOL_CALL,
		input_schema=SearchInput,
		output_schema=SearchOutput,
		implementation=impl_search,
		description="Web search",
	)

	ag.add_instruction(plan)
	ag.add_instruction(verify)
	ag.add_instruction(search)
	ag.add_edge("plan", "verify")
	ag.add_edge("verify", "search")
	ag.set_entry_point("plan")
	ag.set_finish_point("search")
	return ag


def build_stage3(query: str) -> ArbiterGraph:
	policy = PolicyConfig(policy_id="stage3", description="Compress with judged confidence", rules=[])
	ag = ArbiterGraph(policy_config=policy, enable_observability=True)

	plan = InstructionBinding(
		id="plan",
		instruction_type=InstructionType.GENERATE,
		input_schema=PlanInput,
		output_schema=PlanOutput,
		implementation=impl_plan,
		description="Plan",
	)

	search = InstructionBinding(
		id="search",
		instruction_type=InstructionType.TOOL_CALL,
		input_schema=SearchInput,
		output_schema=SearchOutput,
		implementation=impl_search,
		description="Web search",
	)

	compress = InstructionBinding(
		id="compress",
		instruction_type=InstructionType.COMPRESS,
		input_schema=CompressInput,
		output_schema=CompressOutput,
		implementation=impl_compress,
		description="Summarize results",
	)

	ag.add_instruction(plan)
	ag.add_instruction(search)
	ag.add_instruction(compress)
	ag.add_edge("plan", "search")
	ag.add_edge("search", "compress")
	ag.set_entry_point("plan")
	ag.set_finish_point("compress")
	return ag


def build_stage4(query: str) -> ArbiterGraph:
	policy = PolicyConfig(policy_id="stage4", description="Evaluate & Replan & Report", rules=[])
	ag = ArbiterGraph(policy_config=policy, enable_observability=True)

	plan = InstructionBinding(
		id="plan",
		instruction_type=InstructionType.GENERATE,
		input_schema=PlanInput,
		output_schema=PlanOutput,
		implementation=impl_plan,
		description="Plan",
	)

	evalp = InstructionBinding(
		id="evaluate",
		instruction_type=InstructionType.EVALUATE_PROGRESS,
		input_schema=EvalInput,
		output_schema=EvalOutput,
		implementation=impl_eval,
		description="Evaluate progress",
	)

	replan = InstructionBinding(
		id="replan",
		instruction_type=InstructionType.REPLAN,
		input_schema=ReplanInput,
		output_schema=ReplanOutput,
		implementation=impl_replan,
		description="Replan",
	)

	report = InstructionBinding(
		id="report",
		instruction_type=InstructionType.GENERATE,
		input_schema=ReportInput,
		output_schema=ReportOutput,
		implementation=impl_report,
		description="Produce final report",
	)

	ag.add_instruction(plan)
	ag.add_instruction(evalp)
	ag.add_instruction(replan)
	ag.add_instruction(report)
	ag.add_edge("plan", "evaluate")
	ag.add_edge("evaluate", "replan")
	ag.add_edge("replan", "report")
	ag.set_entry_point("plan")
	ag.set_finish_point("report")
	return ag


# ==========================
# Run all stages end-to-end
# ==========================

def run(query: str) -> None:
	# Stage 1 (simulate failure)
	s1 = build_stage1(query)
	r1 = s1.execute({"query": query, "force_fail": True})
	print("\n=== Stage 1: Naive (expected brittle) ===")
	print(json.dumps(r1.get_state_summary(), indent=2))

	# Stage 2 (verify then search)
	s2 = build_stage2(query)
	r2 = s2.execute({"query": query, "content": "<html>503 Service Unavailable</html>", "criteria": "signal", "force_fail": False})
	print("\n=== Stage 2: VERIFY + fallback-ready ===")
	print(json.dumps(r2.get_state_summary(), indent=2))

	# Stage 3 (compress results)
	s3 = build_stage3(query)
	r3 = s3.execute({"query": query, "force_fail": False})
	print("\n=== Stage 3: Governed memory (COMPRESS) ===")
	print(json.dumps(r3.get_state_summary(), indent=2))
	compressed = r3.user_state.get("summary", "")

	# Stage 4 (evaluate -> replan -> report)
	s4 = build_stage4(query)
	r4 = s4.execute({"query": query, "notes": compressed[:200], "step": 7, "plan": "naive-plan", "issue": "need_focus", "summary": compressed})
	print("\n=== Stage 4: Evaluate + Replan + Report ===")
	print(json.dumps(r4.get_state_summary(), indent=2))
	print("\n=== Final Report ===\n")
	print(r4.user_state.get("report", "<no report>"))


def main() -> None:
	parser = argparse.ArgumentParser(description="Real Walkthrough Demo")
	parser.add_argument("--query", required=True, help="Topic to research (e.g., 'NVIDIA Q2 earnings')")
	args = parser.parse_args()
	run(args.query)


if __name__ == "__main__":
	main()
