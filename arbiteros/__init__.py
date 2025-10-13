"""
ArbiterOS-Core: A formal operating system paradigm for reliable AI agents.

This library provides a neuro-symbolic governance layer for LangGraph-based agents,
enabling reliable, auditable, and secure agent execution through formal policy enforcement.
"""

__version__ = "0.1.0"
__author__ = "ArbiterOS Team"
__email__ = "team@arbiteros.dev"

from .core.arbiter_graph import ArbiterGraph
from .core.policy_engine import PolicyEngine, PolicyConfig, PolicyRule, PolicyRuleType
from .core.instruction_binding import InstructionBinding, InstructionType, InstructionResult
from .core.managed_state import ManagedState
from .core.observability import FlightDataRecorder

# Optional Redis checkpointer helper
import os

def build_redis_checkpointer_from_env():
	"""Return a RedisSaver instance if REDIS_URL is set, else None."""
	try:
		from langgraph.checkpoint.redis import RedisSaver
		url = os.getenv("REDIS_URL")
		if not url:
			return None
		return RedisSaver.from_url(url)
	except Exception:
		return None

__all__ = [
	"ArbiterGraph",
	"PolicyEngine", 
	"PolicyConfig",
	"PolicyRule",
	"PolicyRuleType",
	"InstructionBinding",
	"InstructionType",
	"InstructionResult",
	"ManagedState",
	"FlightDataRecorder",
	"build_redis_checkpointer_from_env",
]
