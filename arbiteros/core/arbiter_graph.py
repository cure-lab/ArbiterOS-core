"""ArbiterGraph - The core governance layer for LangGraph."""

from typing import Any, Dict, List, Optional, Callable, Union
import time
import logging
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from .policy_engine import PolicyEngine, PolicyConfig
from .instruction_binding import InstructionBinding, InstructionType, InstructionResult
from .managed_state import ManagedState
from .observability import FlightDataRecorder


class ArbiterGraph:
	"""
	ArbiterGraph - The symbolic governor for LangGraph-based agents.
	
	This class wraps LangGraph's StateGraph with governance capabilities,
	implementing the "Kernel-as-Governor" paradigm from the ArbiterOS paper.
	"""
	
	def __init__(
		self,
		policy_config: PolicyConfig,
		checkpoint_saver: Optional[BaseCheckpointSaver] = None,
		enable_observability: bool = True,
		jaeger_endpoint: Optional[str] = None,
		debug: bool = False,
	):
		"""
		Initialize the ArbiterGraph.
		
		Args:
			policy_config: Policy configuration for governance
			checkpoint_saver: Checkpoint saver for state persistence
			enable_observability: Whether to enable observability features
			jaeger_endpoint: Jaeger endpoint for distributed tracing
			debug: Enable strict ManagedState validation after each step
		"""
		self.policy_config = policy_config
		self.policy_engine = PolicyEngine(policy_config)
		self.checkpoint_saver = checkpoint_saver
		self.logger = logging.getLogger(__name__)
		self.debug = debug
		
		# Initialize observability
		self.observability_enabled = enable_observability
		if enable_observability:
			self.flight_recorder = FlightDataRecorder(
				enable_otel=True,
				jaeger_endpoint=jaeger_endpoint
			)
		else:
			self.flight_recorder = None
		
		# Initialize the underlying LangGraph
		self.graph = StateGraph(ManagedState)
		self.instruction_bindings: Dict[str, InstructionBinding] = {}
		self.execution_id: Optional[str] = None
		
		# Register the central arbiter
		self.graph.add_node("arbiter", self._arbiter_function)
	
	def _validate_state_if_debug(self, state: ManagedState) -> None:
		"""Re-validate ManagedState when debug mode is enabled."""
		if not self.debug:
			return
		# Round-trip through dict -> model to catch contract issues early
		try:
			_ = ManagedState.from_dict(state.to_dict())
		except Exception as e:
			raise ValueError(f"ManagedState validation failed (debug mode): {e}") from e
	
	def add_instruction(
		self, 
		binding: InstructionBinding, 
		dependencies: Optional[List[str]] = None
	) -> None:
		"""
		Add an instruction binding to the graph.
		
		Args:
			binding: Instruction binding to add
			dependencies: List of instruction IDs this depends on
		"""
		self.instruction_bindings[binding.id] = binding
		
		# Create a wrapped function for the instruction
		def instruction_wrapper(state: ManagedState) -> ManagedState:
			return self._execute_instruction(binding, state)
		
		# Add the instruction as a node
		self.graph.add_node(binding.id, instruction_wrapper)
		
		# Add dependencies if specified
		if dependencies:
			for dep in dependencies:
				if dep in self.instruction_bindings:
					self.graph.add_edge(dep, binding.id)
	
	def add_edge(self, from_instruction: str, to_instruction: str) -> None:
		"""Add an edge between instructions."""
		if from_instruction in self.instruction_bindings and to_instruction in self.instruction_bindings:
			self.graph.add_edge(from_instruction, to_instruction)
		else:
			raise ValueError(f"One or both instructions not found: {from_instruction} -> {to_instruction}")
	
	def set_entry_point(self, instruction_id: str) -> None:
		"""Set the entry point for the graph."""
		if instruction_id not in self.instruction_bindings:
			raise ValueError(f"Instruction not found: {instruction_id}")
		self.graph.set_entry_point(instruction_id)
	
	def set_finish_point(self, instruction_id: str) -> None:
		"""Set the finish point for the graph."""
		if instruction_id not in self.instruction_bindings:
			raise ValueError(f"Instruction not found: {instruction_id}")
		self.graph.add_edge(instruction_id, END)
	
	def compile(self) -> Any:
		"""Compile the graph for execution."""
		return self.graph.compile(checkpointer=self.checkpoint_saver)
	
	def _arbiter_function(self, state: ManagedState) -> ManagedState:
		"""
		The central arbiter function that governs execution.
		
		This implements the core governance logic, making deterministic
		routing decisions based on policy evaluation.
		"""
		if not self.execution_id:
			self.execution_id = state.os_metadata.execution_id
		
		# Record arbiter activation
		if self.flight_recorder:
			self.flight_recorder.record_event(
				"arbiter_activation",
				{"execution_id": self.execution_id},
				execution_id=self.execution_id
			)
		
		# Get the current instruction
		current_instruction = state.os_metadata.current_instruction
		
		if not current_instruction:
			# No current instruction, this shouldn't happen
			self.logger.error("Arbiter called with no current instruction")
			self._validate_state_if_debug(state)
			return state
		
		# Get the instruction binding
		binding = self.instruction_bindings.get(current_instruction)
		if not binding:
			self.logger.error(f"Instruction binding not found: {current_instruction}")
			self._validate_state_if_debug(state)
			return state
		
		# Evaluate policies
		rule_results = self.policy_engine.evaluate_rules(
			binding.instruction_type.value,
			state.to_dict(),
			{"execution_id": self.execution_id}
		)
		
		# Record policy evaluation
		if self.flight_recorder:
			self.flight_recorder.record_policy_evaluation(
				current_instruction,
				rule_results,
				self.execution_id
			)
		
		# Check if execution should be allowed
		allowed, evaluation_results = self.policy_engine.should_allow_execution(
			binding.instruction_type.value,
			state.to_dict(),
			{"execution_id": self.execution_id}
		)
		
		if not allowed:
			# Policy violation - determine action
			action = self._determine_violation_action(rule_results)
			
			if action == "INTERRUPT":
				state.trigger_interrupt("Policy violation")
				if self.flight_recorder:
					self.flight_recorder.record_interrupt(
						current_instruction,
						"Policy violation",
						self.execution_id
					)
			elif action == "FALLBACK":
				state.trigger_fallback("Policy violation")
				if self.flight_recorder:
					self.flight_recorder.record_fallback_triggered(
						current_instruction,
						"Policy violation",
						self.execution_id
					)
			else:
				# Log violation and continue
				for result in rule_results:
					if not result.get("passed", True):
						state.add_policy_violation(result)
						if self.flight_recorder:
							self.flight_recorder.record_policy_violation(
								current_instruction,
								result,
								self.execution_id
							)
		
		# Record arbiter decision
		if self.flight_recorder:
			self.flight_recorder.record_arbiter_decision(
				current_instruction,
				"ALLOW" if allowed else "BLOCK",
				"Policy evaluation completed",
				self.execution_id
			)
		
		self._validate_state_if_debug(state)
		return state
	
	def _determine_violation_action(self, rule_results: List[Dict[str, Any]]) -> str:
		"""Determine the action to take for policy violations."""
		# Check for critical violations
		critical_violations = [
			r for r in rule_results 
			if not r.get("passed", True) and r.get("severity") == "critical"
		]
		
		if critical_violations:
			return "INTERRUPT"
		
		# Check for fallback triggers
		fallback_violations = [
			r for r in rule_results 
			if not r.get("passed", True) and r.get("action") == "FALLBACK"
		]
		
		if fallback_violations:
			return "FALLBACK"
		
		# Default to logging
		return "LOG"
	
	def _execute_instruction(self, binding: InstructionBinding, state: ManagedState) -> ManagedState:
		"""
		Execute an instruction with proper governance and observability.
		
		Args:
			binding: Instruction binding to execute
			state: Current managed state
			
		Returns:
			Updated managed state
		"""
		start_time = time.time()
		
		# Record instruction start
		if self.flight_recorder:
			self.flight_recorder.record_instruction_start(
				binding.id,
				binding.instruction_type.value,
				state.os_metadata.execution_id
			)
		
		try:
			# Set current instruction
			state.set_current_instruction(binding.id)
			
			# Execute the instruction
			result = binding.execute(state.to_dict())
			
			# Update state with result
			state.update_user_state(result)
			
			# Calculate execution metrics
			execution_time = time.time() - start_time
			tokens_used = result.get("tokens_used", 0)
			
			# Update resource usage
			state.update_resource_usage(tokens_used, execution_time)
			state.update_latency_metric(binding.id, execution_time)
			
			# Record successful completion
			if self.flight_recorder:
				self.flight_recorder.record_instruction_end(
					binding.id,
					True,
					execution_time,
					tokens_used
				)
			
			self.logger.info(f"Instruction {binding.id} completed successfully in {execution_time:.2f}s")
			
		except Exception as e:
			# Handle execution error
			execution_time = time.time() - start_time
			error_msg = str(e)
			
			# Add error to state
			state.add_error({
				"instruction_id": binding.id,
				"error": error_msg,
				"error_type": type(e).__name__,
				"execution_time": execution_time
			})
			
			# Record error
			if self.flight_recorder:
				self.flight_recorder.record_error(
					binding.id,
					error_msg,
					type(e).__name__,
					state.os_metadata.execution_id
				)
				self.flight_recorder.record_instruction_end(
					binding.id,
					False,
					execution_time,
					error=error_msg
				)
			
			self.logger.error(f"Instruction {binding.id} failed: {error_msg}")
			
			# Check if we should trigger fallback
			if binding.instruction_type in [InstructionType.TOOL_CALL, InstructionType.GENERATE]:
				# Try to find a FALLBACK instruction
				fallback_binding = self._find_fallback_instruction()
				if fallback_binding:
					state.trigger_fallback(f"Error in {binding.id}: {error_msg}")
					if self.flight_recorder:
						self.flight_recorder.record_fallback_triggered(
							binding.id,
							f"Error: {error_msg}",
							state.os_metadata.execution_id
						)
		
		self._validate_state_if_debug(state)
		return state
	
	def _find_fallback_instruction(self) -> Optional[InstructionBinding]:
		"""Find a FALLBACK instruction binding."""
		for binding in self.instruction_bindings.values():
			if binding.instruction_type == InstructionType.FALLBACK:
				return binding
		return None
	
	def execute(
		self, 
		initial_state: Optional[Dict[str, Any]] = None,
		config: Optional[Dict[str, Any]] = None
	) -> ManagedState:
		"""
		Execute the governed graph.
		
		Args:
			initial_state: Initial state for execution
			config: Execution configuration
			
		Returns:
			Final managed state
		"""
		# Create initial managed state
		if initial_state is None:
			initial_state = {}
		
		managed_state = ManagedState()
		managed_state.update_user_state(initial_state)
		
		# Set execution ID
		self.execution_id = managed_state.os_metadata.execution_id
		
		# Record execution start
		if self.flight_recorder:
			self.flight_recorder.record_event(
				"execution_start",
				{"execution_id": self.execution_id},
				execution_id=self.execution_id
			)
		
		# Compile and execute the graph
		compiled_graph = self.compile()
		
		try:
			# Execute the graph
			result = compiled_graph.invoke(
				managed_state,
				config=config or {}
			)
			
			# Ensure result is a ManagedState object
			if isinstance(result, dict):
				result = ManagedState.from_dict(result)
			
			# Record execution completion
			if self.flight_recorder:
				self.flight_recorder.record_event(
					"execution_complete",
					{
						"execution_id": self.execution_id,
						"success": result.is_healthy()
					},
					execution_id=self.execution_id
				)
			
			self._validate_state_if_debug(result)
			return result
			
		except Exception as e:
			# Record execution error
			if self.flight_recorder:
				self.flight_recorder.record_error(
					"execution",
					str(e),
					type(e).__name__,
					self.execution_id
				)
			
			raise
	
	def get_execution_trace(self, execution_id: Optional[str] = None) -> List[Dict[str, Any]]:
		"""Get the execution trace for debugging."""
		if not self.flight_recorder:
			return []
		
		target_id = execution_id or self.execution_id
		if not target_id:
			return []
		
		return self.flight_recorder.get_execution_trace(target_id)
	
	def get_trace_summary(self, execution_id: Optional[str] = None) -> Dict[str, Any]:
		"""Get a summary of the execution trace."""
		if not self.flight_recorder:
			return {}
		
		target_id = execution_id or self.execution_id
		if not target_id:
			return {}
		
		return self.flight_recorder.get_trace_summary(target_id)
	
	def export_trace(self, execution_id: Optional[str] = None, format: str = "json") -> str:
		"""Export the execution trace."""
		if not self.flight_recorder:
			return "{}"
		
		target_id = execution_id or self.execution_id
		if not target_id:
			return "{}"
		
		return self.flight_recorder.export_trace(target_id, format)
