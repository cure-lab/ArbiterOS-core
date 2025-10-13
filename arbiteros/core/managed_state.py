"""Managed State for ArbiterOS - the central source of truth."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
import json


class StateMetadata(BaseModel):
    """Metadata for the managed state."""
    
    model_config = ConfigDict(extra="forbid")
    
    # Execution tracking
    execution_id: str = Field(..., description="Unique execution identifier")
    start_time: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    # Instruction tracking
    current_instruction: Optional[str] = Field(default=None)
    instruction_history: List[str] = Field(default_factory=list)
    recent_instructions: List[str] = Field(default_factory=list, max_length=5)
    
    # Resource tracking
    total_tokens: int = Field(default=0)
    execution_time: float = Field(default=0.0)
    retry_count: int = Field(default=0)
    
    # Governance state
    policy_violations: List[Dict[str, Any]] = Field(default_factory=list)
    verification_status: Optional[Dict[str, Any]] = Field(default=None)
    interrupt_reason: Optional[str] = Field(default=None)
    
    # Error tracking
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    fallback_triggered: bool = Field(default=False)
    
    # Performance metrics
    latency_metrics: Dict[str, float] = Field(default_factory=dict)
    cost_metrics: Dict[str, Any] = Field(default_factory=dict)


class ManagedState(BaseModel):
    """
    The central managed state for ArbiterOS.
    
    This serves as the single source of truth for the agent's execution,
    providing both user-accessible state and protected OS metadata.
    """
    
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    
    # User-accessible state (the "application state")
    user_state: Dict[str, Any] = Field(default_factory=dict)
    
    # Protected OS metadata (governance and system state)
    os_metadata: StateMetadata = Field(default_factory=lambda: StateMetadata(execution_id=ManagedState._generate_execution_id()))
    
    # Additional system state
    system_state: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data):
        """Initialize managed state with proper metadata handling."""
        # Ensure os_metadata is properly initialized
        if 'os_metadata' not in data or data['os_metadata'] is None:
            data['os_metadata'] = StateMetadata(execution_id=self._generate_execution_id())
        super().__init__(**data)
    
    @staticmethod
    def _generate_execution_id() -> str:
        """Generate a unique execution ID."""
        import uuid
        return str(uuid.uuid4())
    
    def update_user_state(self, updates: Dict[str, Any]) -> None:
        """Update the user-accessible state."""
        self.user_state.update(updates)
        self.os_metadata.last_updated = datetime.now()
    
    def update_os_metadata(self, updates: Dict[str, Any]) -> None:
        """Update the protected OS metadata."""
        for key, value in updates.items():
            if hasattr(self.os_metadata, key):
                setattr(self.os_metadata, key, value)
        self.os_metadata.last_updated = datetime.now()
    
    def add_instruction_to_history(self, instruction_id: str) -> None:
        """Add an instruction to the execution history."""
        self.os_metadata.instruction_history.append(instruction_id)
        self.os_metadata.recent_instructions.append(instruction_id)
        
        # Keep only the last 5 instructions in recent_instructions
        if len(self.os_metadata.recent_instructions) > 5:
            self.os_metadata.recent_instructions.pop(0)
    
    def set_current_instruction(self, instruction_id: str) -> None:
        """Set the current instruction being executed."""
        self.os_metadata.current_instruction = instruction_id
        self.add_instruction_to_history(instruction_id)
    
    def add_policy_violation(self, violation: Dict[str, Any]) -> None:
        """Add a policy violation to the metadata."""
        violation["timestamp"] = datetime.now().isoformat()
        self.os_metadata.policy_violations.append(violation)
    
    def add_error(self, error: Dict[str, Any]) -> None:
        """Add an error to the metadata."""
        error["timestamp"] = datetime.now().isoformat()
        self.os_metadata.errors.append(error)
    
    def set_verification_status(self, status: Dict[str, Any]) -> None:
        """Set the verification status."""
        self.os_metadata.verification_status = status
        self.os_metadata.last_updated = datetime.now()
    
    def trigger_fallback(self, reason: str) -> None:
        """Trigger a fallback mechanism."""
        self.os_metadata.fallback_triggered = True
        self.os_metadata.interrupt_reason = f"FALLBACK: {reason}"
        self.os_metadata.last_updated = datetime.now()
    
    def trigger_interrupt(self, reason: str) -> None:
        """Trigger an interrupt."""
        self.os_metadata.interrupt_reason = reason
        self.os_metadata.last_updated = datetime.now()
    
    def update_resource_usage(self, tokens: int, execution_time: float) -> None:
        """Update resource usage metrics."""
        self.os_metadata.total_tokens += tokens
        self.os_metadata.execution_time += execution_time
        self.os_metadata.last_updated = datetime.now()
    
    def update_latency_metric(self, operation: str, latency: float) -> None:
        """Update latency metrics for a specific operation."""
        self.os_metadata.latency_metrics[operation] = latency
        self.os_metadata.last_updated = datetime.now()
    
    def update_cost_metric(self, operation: str, cost: Any) -> None:
        """Update cost metrics for a specific operation."""
        self.os_metadata.cost_metrics[operation] = cost
        self.os_metadata.last_updated = datetime.now()
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current state."""
        return {
            "execution_id": self.os_metadata.execution_id,
            "current_instruction": self.os_metadata.current_instruction,
            "total_tokens": self.os_metadata.total_tokens,
            "execution_time": self.os_metadata.execution_time,
            "policy_violations": len(self.os_metadata.policy_violations),
            "errors": len(self.os_metadata.errors),
            "fallback_triggered": self.os_metadata.fallback_triggered,
            "interrupt_reason": self.os_metadata.interrupt_reason,
            "last_updated": self.os_metadata.last_updated.isoformat()
        }
    
    def get_execution_trace(self) -> List[Dict[str, Any]]:
        """Get a detailed execution trace."""
        trace = []
        
        for i, instruction_id in enumerate(self.os_metadata.instruction_history):
            trace.append({
                "step": i + 1,
                "instruction_id": instruction_id,
                "timestamp": self.os_metadata.last_updated.isoformat()
            })
        
        return trace
    
    def is_healthy(self) -> bool:
        """Check if the state is in a healthy condition."""
        return (
            len(self.os_metadata.errors) == 0 and
            not self.os_metadata.fallback_triggered and
            self.os_metadata.interrupt_reason is None
        )
    
    def requires_attention(self) -> bool:
        """Check if the state requires human attention."""
        return (
            len(self.os_metadata.policy_violations) > 0 or
            len(self.os_metadata.errors) > 0 or
            self.os_metadata.fallback_triggered or
            self.os_metadata.interrupt_reason is not None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the managed state to a dictionary."""
        return {
            "user_state": self.user_state,
            "os_metadata": self.os_metadata.model_dump(),
            "system_state": self.system_state
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManagedState":
        """Create a ManagedState from a dictionary."""
        if "os_metadata" in data and isinstance(data["os_metadata"], dict):
            data["os_metadata"] = StateMetadata(**data["os_metadata"])
        return cls(**data)
    
    def serialize(self) -> str:
        """Serialize the state to JSON."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def deserialize(cls, data: str) -> "ManagedState":
        """Deserialize the state from JSON."""
        return cls.from_dict(json.loads(data))
