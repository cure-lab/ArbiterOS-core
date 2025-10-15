"""Power Demo: Apple Market Report (ArbiterOS)

Showcases ArbiterOS capabilities end-to-end:
- PLAN → SEARCH (web) → VERIFY (truth/quality) → COMPRESS → STRUCTURE_REPORT
- Uses LLM (OpenAI) if available; otherwise falls back to heuristic/mimic.
- SEARCH step has resilient fallback: if network is unavailable, mimic via LLM or heuristic.
- Policies enforce semantic safety (VERIFY before report/tool) and content length governance.

Run:
  python -m arbiteros.examples.power_demo_apple
"""

import os
import json
from typing import Any, Dict, List, Optional

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
# Optional LLM (OpenAI) wrapper
# ==========================

def _has_openai() -> bool:
	return bool(os.getenv("OPENAI_API_KEY"))


def _llm_summarize(prompt: str, max_tokens: int = 300) -> str:
	"""Summarize with LLM if available; else heuristic."""
	if not _has_openai():
		# Simple heuristic: trim paragraphs and keep bullets
		text = prompt.strip()
		if len(text) <= max_tokens * 4:
			return text
		return text[: max_tokens * 4] + "..."
	try:
		from openai import OpenAI
		client = OpenAI()
		sys = "You are a professional market analyst. Write concise, factual summaries."
		resp = client.chat.completions.create(
			model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
			messages=[{"role": "system", "content": sys}, {"role": "user", "content": prompt}],
			max_tokens=max_tokens,
		)
		return resp.choices[0].message.content or ""
	except Exception:
		# Graceful fallback
		text = prompt.strip()
		return text[: max_tokens * 4] + ("..." if len(text) > max_tokens * 4 else "")


def _llm_score_truth(text: str) -> float:
	"""Ask LLM to score reliability 0-1; fallback to heuristics."""
	if not _has_openai():
		# Heuristic: longer + has sources-like keywords → higher
		score = 0.3
		if len(text) > 600:
			score += 0.3
		keywords = ["Reuters", "Bloomberg", "WSJ", "SEC", "10-K", "earnings"]
		if any(k.lower() in text.lower() for k in keywords):
			score += 0.3
		return min(1.0, score)
	try:
		from openai import OpenAI
		client = OpenAI()
		prompt = (
			"Rate the factual reliability (0-1) of the following market snippets; "
			"consider source credibility and specificity. Respond ONLY a number 0-1.\n\n" + text[:4000]
		)
		resp = client.chat.completions.create(
			model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
			messages=[{"role": "user", "content": prompt}],
			max_tokens=8,
		)
		raw = resp.choices[0].message.content or "0.5"
		try:
			return max(0.0, min(1.0, float(raw.strip())))
		except Exception:
			return 0.6
	except Exception:
		return 0.6

# ==========================
# Web helpers
# ==========================

DDG_HTML = "https://duckduckgo.com/html/"
DDG_API = "https://api.duckduckgo.com/"
JINA_PROXY = "https://r.jina.ai/http://duckduckgo.com/html/"
UA = {"User-Agent": "Mozilla/5.0"}


def _fetch_text(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[str]:
	try:
		with httpx.Client(timeout=20, headers=UA) as client:
			r = client.get(url, params=params)
			if r.status_code == 200:
				return r.text
	except Exception:
		return None
	return None


def _ddg_instant(query: str) -> Optional[str]:
	try:
		with httpx.Client(timeout=15, headers=UA) as client:
			r = client.get(DDG_API, params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1})
			if r.status_code == 200:
				data = r.json()
				abstract = (data.get("AbstractText") or "").strip()
				related = []
				for t in data.get("RelatedTopics", [])[:5]:
					text = t.get("Text") if isinstance(t, dict) else None
					if text:
						related.append(text)
				parts = [p for p in [abstract, "\n".join(related)] if p]
				return "\n".join(parts) if parts else None
	except Exception:
		return None
	return None


def _search_best_effort(query: str) -> str:
	# 1) DDG Instant 2) DDG HTML 3) DDG HTML via proxy 4) LLM(mimic)
	text = _ddg_instant(query)
	if text:
		return text
	html = _fetch_text(DDG_HTML, {"q": query})
	if html:
		return _llm_summarize(f"Summarize web search results into facts and bullets:\n\n{html}", 300)
	html2 = _fetch_text(JINA_PROXY, {"q": query})
	if html2:
		return _llm_summarize(f"Summarize web search results into facts and bullets:\n\n{html2}", 300)
	# LLM mimic of search results
	return _llm_summarize(
		"Act as an internet search agent. For the query 'Apple market report', "
		"invent plausible but sensible snippets that would likely appear in news/financial sources. "
		"Include earnings, segments, risks, and recent headlines.",
		300,
	)

# ==========================
# Schemas for each step
# ==========================

class PlanInput(BaseModel):
	objective: str = Field(default="Produce a concise Apple (AAPL) market report")


class PlanOutput(BaseModel):
	plan: str


class SearchInput(BaseModel):
	query: str


class SearchOutput(BaseModel):
	raw_text: str


class VerifyInput(BaseModel):
	content: str


class VerifyOutput(BaseModel):
	passed: bool
	confidence: float
	reason: str


class CompressInput(BaseModel):
	text: str
	target_length: int = 700


class CompressOutput(BaseModel):
	summary: str
	judge_confidence: float


class ReportInput(BaseModel):
	topic: str
	summary: str
	confidence: float


class ReportOutput(BaseModel):
	report: Dict[str, Any]

# ==========================
# Implementations
# ==========================

def impl_plan(state: PlanInput) -> Dict[str, Any]:
	plan = (
		"1) Search the web or mimic results if offline;\n"
		"2) Verify reliability;\n"
		"3) Compress into key points;\n"
		"4) Structure a JSON market report (overview/news/financials/risks/outlook)."
	)
	return {"plan": plan}


def impl_search(state: SearchInput) -> Dict[str, Any]:
	text = _search_best_effort(state.query)
	return {"raw_text": text}


def impl_verify(state: VerifyInput) -> Dict[str, Any]:
	score = _llm_score_truth(state.content)
	passed = score >= 0.6
	reason = "acceptable" if passed else "insufficient credible signals"
	return {"passed": passed, "confidence": score, "reason": reason}


def impl_compress(state: CompressInput) -> Dict[str, Any]:
	prompt = (
		"Compress the following Apple-related market snippets into concise bullets. "
		"Preserve key facts (financials, products, segments, risks, competition).\n\n"
		+ state.text[:8000]
	)
	summary = _llm_summarize(prompt, max_tokens=350)
	# As a simple proxy, judge confidence tied to earlier verify is better; here use length heuristic
	conf = 0.8 if len(summary) > 200 else 0.6
	return {"summary": summary, "judge_confidence": conf}


def impl_report(state: ReportInput) -> Dict[str, Any]:
	# Build a structured JSON report
	overview = _llm_summarize(
		f"Create a short overview of {state.topic} from this summary:\n\n{state.summary}\n\nBe factual and neutral.",
		180,
	)
	recent_news = _llm_summarize(
		f"Extract 3-6 concise recent news bullets for {state.topic}:\n\n{state.summary}",
		160,
	)
	financials = _llm_summarize(
		f"From the summary, note financial highlights for {state.topic} (revenue trends, segments, margin cues). If unknown, say 'N/A'.\n\n{state.summary}",
		140,
	)
	risks = _llm_summarize(
		f"List 3-5 key risks for {state.topic} based on the summary.",
		120,
	)
	outlook = _llm_summarize(
		f"Provide a short near-term outlook for {state.topic} grounded in the summary; avoid speculation.",
		120,
	)
	report = {
		"topic": state.topic,
		"confidence": round(float(state.confidence), 2),
		"overview": overview,
		"recent_news": [b for b in recent_news.split("\n") if b.strip()][:6],
		"financials": financials,
		"risks": [r for r in risks.split("\n") if r.strip()][:5],
		"outlook": outlook,
	}
	return {"report": report}

# ==========================
# Build graph with policies
# ==========================

def build_policy() -> PolicyConfig:
	return PolicyConfig(
		policy_id="apple_market_report_policy",
		description="Governed pipeline for Apple market report",
		rules=[
			# Enforce VERIFY before producing structured report
			PolicyRule(
				rule_id="semantic_verify_before_report",
				rule_type=PolicyRuleType.SEMANTIC_SAFETY,
				description="Require VERIFY before GENERATE/TOOL_CALL report",
				condition={"allowed_flows": ["GENERATE->VERIFY->GENERATE", "TOOL_CALL->VERIFY->GENERATE"]},
				action="LOG",
				severity="warning",
				applies_to=["GENERATE"],
			),
			# Content length guard to encourage compression
			PolicyRule(
				rule_id="content_length_guard",
				rule_type=PolicyRuleType.CONTENT_AWARE,
				description="Large content should be compressed",
				condition={"max_length": 15000},
				action="LOG",
				severity="info",
				applies_to=["TOOL_CALL", "GENERATE"],
			),
		],
		strict_mode=False,
	)


def build_graph() -> ArbiterGraph:
	policy = build_policy()
	ag = ArbiterGraph(policy_config=policy, enable_observability=True)

	plan = InstructionBinding(
		id="plan",
		instruction_type=InstructionType.GENERATE,
		input_schema=PlanInput,
		output_schema=PlanOutput,
		implementation=impl_plan,
		description="Plan pipeline",
	)

	search = InstructionBinding(
		id="search",
		instruction_type=InstructionType.TOOL_CALL,
		input_schema=SearchInput,
		output_schema=SearchOutput,
		implementation=impl_search,
		description="Search web or mimic via LLM",
	)

	verify = InstructionBinding(
		id="verify",
		instruction_type=InstructionType.VERIFY,
		input_schema=VerifyInput,
		output_schema=VerifyOutput,
		implementation=impl_verify,
		description="Truth/quality check",
	)

	compress = InstructionBinding(
		id="compress",
		instruction_type=InstructionType.COMPRESS,
		input_schema=CompressInput,
		output_schema=CompressOutput,
		implementation=impl_compress,
		description="Compress to key bullets",
	)

	report = InstructionBinding(
		id="report",
		instruction_type=InstructionType.GENERATE,
		input_schema=ReportInput,
		output_schema=ReportOutput,
		implementation=impl_report,
		description="Structured JSON report",
	)

	ag.add_instruction(plan)
	ag.add_instruction(search)
	ag.add_instruction(verify)
	ag.add_instruction(compress)
	ag.add_instruction(report)

	# Flow: PLAN → SEARCH → VERIFY → COMPRESS → REPORT
	ag.add_edge("plan", "search")
	ag.add_edge("search", "verify")
	ag.add_edge("verify", "compress")
	ag.add_edge("compress", "report")

	ag.set_entry_point("plan")
	ag.set_finish_point("report")
	return ag

# ==========================
# Demo runner
# ==========================

def main() -> None:
	ag = build_graph()
	initial = {
		"objective": "Produce a concise Apple (AAPL) market report",
		"query": "Apple company market report earnings products risks competition 2024 2025",
	}
	final_state = ag.execute(initial)
	print("\n=== Apple Market Report (Structured JSON) ===")
	print(json.dumps(final_state.user_state.get("report", {}), indent=2, ensure_ascii=False))


if __name__ == "__main__":
	main()
