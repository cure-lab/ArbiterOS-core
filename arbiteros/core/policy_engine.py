"""Policy Engine for declarative governance enforcement."""

from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, validator
import json


class PolicyRuleType(str, Enum):
	"""Types of policy rules that can be enforced."""
	
	# Semantic Safety Rules
	SEMANTIC_SAFETY = "semantic_safety"
	
	# Content-Aware Governance
	CONTENT_AWARE = "content_aware"
	
	# Resource Management
	RESOURCE_LIMIT = "resource_limit"
	
	# Conditional Resilience
	CONDITIONAL_RESILIENCE = "conditional_resilience"
	
	# Custom Rules
	CUSTOM = "custom"


class PolicyRule(BaseModel):
	"""Individual policy rule definition."""
	
	model_config = ConfigDict(extra="forbid")
	
	rule_id: str = Field(..., description="Unique identifier for this rule")
	rule_type: PolicyRuleType = Field(..., description="Type of policy rule")
	description: str = Field(..., description="Human-readable description")
	
	# Rule conditions
	condition: Dict[str, Any] = Field(..., description="Condition for rule activation")
	
	# Rule actions
	action: str = Field(..., description="Action to take when rule is violated")
	action_params: Optional[Dict[str, Any]] = Field(
		default=None, 
		description="Parameters for the action"
	)
	
	# Rule metadata
	severity: str = Field(default="warning", description="Severity level: info, warning, error, critical")
	enabled: bool = Field(default=True, description="Whether this rule is active")
	
	# Execution context
	applies_to: List[str] = Field(
		default_factory=list,
		description="List of instruction types this rule applies to"
	)
	priority: int = Field(default=0, description="Rule priority (higher = more important)")


class PolicyConfig(BaseModel):
	"""Configuration for the policy engine."""
	
	model_config = ConfigDict(extra="forbid")
	
	# Policy identification
	policy_id: str = Field(..., description="Unique identifier for this policy")
	version: str = Field(default="1.0.0", description="Policy version")
	description: str = Field(..., description="Human-readable policy description")
	
	# Rules
	rules: List[PolicyRule] = Field(default_factory=list, description="List of policy rules")
	
	# Execution environment
	environment: str = Field(default="standard", description="Execution environment (executor, strategist, etc.)")
	
	# Global settings
	strict_mode: bool = Field(default=True, description="Whether to enforce all rules strictly")
	allow_override: bool = Field(default=False, description="Whether rules can be overridden")
	
	# Resource limits
	max_tokens: Optional[int] = Field(default=None, description="Maximum tokens per execution")
	max_execution_time: Optional[float] = Field(default=None, description="Maximum execution time in seconds")
	max_retries: int = Field(default=3, description="Maximum retries for failed instructions")
	
	# Verification settings
	require_verification: bool = Field(default=True, description="Whether to require verification for high-stakes actions")
	verification_confidence_threshold: float = Field(
		default=0.8, 
		description="Minimum confidence for probabilistic verification"
	)
	
	def get_rules_for_instruction(self, instruction_type: str) -> List[PolicyRule]:
		"""Get all rules that apply to a specific instruction type."""
		return [
			rule for rule in self.rules 
			if rule.enabled and (not rule.applies_to or instruction_type in rule.applies_to)
		]
	
	def get_rule_by_id(self, rule_id: str) -> Optional[PolicyRule]:
		"""Get a specific rule by ID."""
		for rule in self.rules:
			if rule.rule_id == rule_id:
				return rule
		return None


class PolicyEngine:
	"""Centralized policy engine for governance enforcement."""
	
	def __init__(self, config: PolicyConfig):
		"""Initialize the policy engine with a configuration."""
		self.config = config
		self._rule_evaluators: Dict[str, Callable] = {}
		self._register_default_evaluators()
		# Precompiled caches for fast lookup per v8.3 guidance
		self._applies_map: Dict[str, List[PolicyRule]] = {}
		self._transition_matrix: Dict[str, bool] = {}
		self._compile_rule_caches()
	
	def _register_default_evaluators(self) -> None:
		"""Register default rule evaluators."""
		self._rule_evaluators = {
			PolicyRuleType.SEMANTIC_SAFETY: self._evaluate_semantic_safety,
			PolicyRuleType.CONTENT_AWARE: self._evaluate_content_aware,
			PolicyRuleType.RESOURCE_LIMIT: self._evaluate_resource_limit,
			PolicyRuleType.CONDITIONAL_RESILIENCE: self._evaluate_conditional_resilience,
			PolicyRuleType.CUSTOM: self._evaluate_custom,
		}
	
	def _compile_rule_caches(self) -> None:
		"""Precompile maps for O(1) lookups where possible."""
		# Build applies_to mapping
		applies: Dict[str, List[PolicyRule]] = {}
		for rule in self.config.rules:
			if not rule.enabled:
				continue
			if not rule.applies_to:
				# Apply to ALL instruction types; store under '*'
				applies.setdefault("*", []).append(rule)
			else:
				for itype in rule.applies_to:
					applies.setdefault(itype, []).append(rule)
		self._applies_map = applies
		# Build a naive transition matrix for semantic_safety allowed_flows
		transition: Dict[str, bool] = {}
		for rule in self.config.rules:
			if not rule.enabled:
				continue
			if rule.rule_type == PolicyRuleType.SEMANTIC_SAFETY:
				allowed = rule.condition.get("allowed_flows", [])
				for flow in allowed:
					transition[flow] = True
		self._transition_matrix = transition
	
	def evaluate_rules(
		self, 
		instruction_type: str, 
		state: Dict[str, Any], 
		context: Optional[Dict[str, Any]] = None
	) -> List[Dict[str, Any]]:
		"""
		Evaluate all applicable rules for an instruction.
		
		Args:
			instruction_type: Type of instruction being executed
			state: Current agent state
			context: Additional execution context
			
		Returns:
			List of rule evaluation results
		"""
		results = []
		# Pull rules for that instruction fast-path, plus global '*'
		applicable_rules = list(self._applies_map.get(instruction_type, [])) + list(self._applies_map.get("*", []))
		
		for rule in applicable_rules:
			try:
				result = self._evaluate_rule(rule, instruction_type, state, context)
				results.append(result)
			except Exception as e:
				# Log error but don't fail the entire evaluation
				results.append({
					"rule_id": rule.rule_id,
					"passed": False,
					"error": str(e),
					"severity": "error"
				})
		
		return results
	
	def _evaluate_rule(
		self, 
		rule: PolicyRule, 
		instruction_type: str, 
		state: Dict[str, Any], 
		context: Optional[Dict[str, Any]]
	) -> Dict[str, Any]:
		"""Evaluate a single rule."""
		evaluator = self._rule_evaluators.get(rule.rule_type)
		if not evaluator:
			return {
				"rule_id": rule.rule_id,
				"passed": False,
				"error": f"No evaluator for rule type: {rule.rule_type}",
				"severity": "error"
			}
		
		try:
			passed, details = evaluator(rule, instruction_type, state, context)
			return {
				"rule_id": rule.rule_id,
				"rule_type": rule.rule_type,
				"passed": passed,
				"details": details,
				"severity": rule.severity,
				"action": rule.action if not passed else None,
				"action_params": rule.action_params if not passed else None
			}
		except Exception as e:
			return {
				"rule_id": rule.rule_id,
				"passed": False,
				"error": str(e),
				"severity": "error"
			}
	
	def _evaluate_semantic_safety(
		self, 
		rule: PolicyRule, 
		instruction_type: str, 
		state: Dict[str, Any], 
		context: Optional[Dict[str, Any]]
	) -> tuple[bool, Dict[str, Any]]:
		"""Evaluate semantic safety rules (e.g., Cognitive -> Execution flow)."""
		# Fast path via transition matrix
		if instruction_type == "TOOL_CALL":
			recent = state.get("os_metadata", {}).get("recent_instructions", [])
			if recent and recent[-1] == "GENERATE":
				if not self._transition_matrix.get("GENERATE->TOOL_CALL", False):
					return False, {
						"violation": "Cognitive instruction followed by Execution without verification",
						"required_action": "Add VERIFY step between GENERATE and TOOL_CALL"
					}
		return True, {"message": "Semantic safety check passed"}
	
	def _evaluate_content_aware(
		self, 
		rule: PolicyRule, 
		instruction_type: str, 
		state: Dict[str, Any], 
		context: Optional[Dict[str, Any]]
	) -> tuple[bool, Dict[str, Any]]:
		"""Evaluate content-aware governance rules."""
		condition = rule.condition
		
		# Example: Check for sensitive content
		if "sensitive_keywords" in condition:
			keywords = condition["sensitive_keywords"]
			content = str(state.get("content", ""))
			
			for keyword in keywords:
				if keyword.lower() in content.lower():
					return False, {
						"violation": f"Sensitive keyword detected: {keyword}",
						"detected_keyword": keyword
					}
		
		# Example: Check content length
		if "max_length" in condition:
			content = str(state.get("content", ""))
			max_length = condition["max_length"]
			
			if len(content) > max_length:
				return False, {
					"violation": f"Content exceeds maximum length: {len(content)} > {max_length}",
					"current_length": len(content),
					"max_length": max_length
				}
		
		return True, {"message": "Content-aware check passed"}
	
	def _evaluate_resource_limit(
		self, 
		rule: PolicyRule, 
		instruction_type: str, 
		state: Dict[str, Any], 
		context: Optional[Dict[str, Any]]
	) -> tuple[bool, Dict[str, Any]]:
		"""Evaluate resource limit rules."""
		condition = rule.condition
		
		# Check token limits
		if "max_tokens" in condition:
			current_tokens = state.get("total_tokens", 0) or state.get("os_metadata", {}).get("total_tokens", 0)
			max_tokens = condition["max_tokens"]
			
			if current_tokens > max_tokens:
				return False, {
					"violation": f"Token limit exceeded: {current_tokens} > {max_tokens}",
					"current_tokens": current_tokens,
					"max_tokens": max_tokens
				}
		
		# Check execution time
		if "max_execution_time" in condition:
			execution_time = state.get("execution_time", 0) or state.get("os_metadata", {}).get("execution_time", 0)
			max_time = condition["max_execution_time"]
			
			if execution_time > max_time:
				return False, {
					"violation": f"Execution time exceeded: {execution_time}s > {max_time}s",
					"current_time": execution_time,
					"max_time": max_time
				}
		
		return True, {"message": "Resource limit check passed"}
	
	def _evaluate_conditional_resilience(
		self, 
		rule: PolicyRule, 
		instruction_type: str, 
		state: Dict[str, Any], 
		context: Optional[Dict[str, Any]]
	) -> tuple[bool, Dict[str, Any]]:
		"""Evaluate conditional resilience rules."""
		condition = rule.condition
		
		# Check if a VERIFY instruction failed
		if "verify_failed" in state and state["verify_failed"]:
			confidence = state.get("verification_confidence", 0)
			threshold = condition.get("confidence_threshold", 0.8)
			
			if confidence < threshold:
				return False, {
					"violation": f"Verification confidence too low: {confidence} < {threshold}",
					"confidence": confidence,
					"threshold": threshold,
					"required_action": "Trigger FALLBACK"
				}
		
		return True, {"message": "Conditional resilience check passed"}
	
	def _evaluate_custom(
		self, 
		rule: PolicyRule, 
		instruction_type: str, 
		state: Dict[str, Any], 
		context: Optional[Dict[str, Any]]
	) -> tuple[bool, Dict[str, Any]]:
		"""Evaluate custom rules."""
		# Custom rule evaluation would be implemented here
		# For now, return a placeholder
		return True, {"message": "Custom rule evaluation not implemented"}
	
	def should_allow_execution(
		self, 
		instruction_type: str, 
		state: Dict[str, Any], 
		context: Optional[Dict[str, Any]] = None
	) -> tuple[bool, List[Dict[str, Any]]]:
		"""
		Determine if an instruction should be allowed to execute.
		
		Returns:
			Tuple of (allowed, evaluation_results)
		"""
		results = self.evaluate_rules(instruction_type, state, context)
		
		# Check for critical failures
		critical_failures = [
			r for r in results 
			if not r.get("passed", True) and r.get("severity") == "critical"
		]
		
		if critical_failures:
			return False, results
		
		# In strict mode, any failure blocks execution
		if self.config.strict_mode:
			failures = [r for r in results if not r.get("passed", True)]
			if failures:
				return False, results
		
		return True, results
