"""Instruction Binding definitions for the Agent Constitution Framework (ACF)."""

from enum import Enum
from typing import Any, Dict, Optional, Type, Union
from pydantic import BaseModel, Field, ConfigDict


class InstructionType(str, Enum):
    """Core instruction types in the Agent Constitution Framework."""
    
    # Cognitive Core - Internal reasoning
    GENERATE = "GENERATE"
    
    # Memory Core - Context management
    COMPRESS = "COMPRESS"
    FILTER = "FILTER"
    LOAD = "LOAD"
    
    # Execution Core - External interactions
    TOOL_CALL = "TOOL_CALL"
    
    # Normative Core - Safety and verification
    VERIFY = "VERIFY"
    CONSTRAIN = "CONSTRAIN"
    FALLBACK = "FALLBACK"
    INTERRUPT = "INTERRUPT"
    
    # Metacognitive Core - Strategic oversight
    MONITOR_RESOURCES = "MONITOR_RESOURCES"
    EVALUATE_PROGRESS = "EVALUATE_PROGRESS"
    REPLAN = "REPLAN"


class InstructionBinding(BaseModel):
    """
    Formal contract for an instruction in the Agent Constitution Framework.
    
    This serves as the "sanitizing firewall" and "device driver" for the
    Hardware Abstraction Layer (HAL).
    """
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    # Core identification
    id: str = Field(..., description="Unique identifier for this instruction")
    instruction_type: InstructionType = Field(..., description="ACF instruction type")
    
    # Schema enforcement
    input_schema: Type[BaseModel] = Field(..., description="Pydantic model for input validation")
    output_schema: Type[BaseModel] = Field(..., description="Pydantic model for output validation")
    
    # Implementation details
    implementation: Any = Field(..., description="The actual function or callable to execute")
    description: Optional[str] = Field(None, description="Human-readable description")
    
    # Governance metadata
    requires_verification: bool = Field(
        default=False, 
        description="Whether this instruction requires verification before execution"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries on failure"
    )
    timeout_seconds: Optional[float] = Field(
        default=None,
        description="Timeout for instruction execution"
    )
    
    # Resource constraints
    estimated_tokens: Optional[int] = Field(
        default=None,
        description="Estimated token consumption for resource planning"
    )
    cost_tier: str = Field(
        default="standard",
        description="Cost tier for model routing (e.g., 'fast', 'standard', 'premium')"
    )
    
    def validate_input(self, data: Dict[str, Any]) -> BaseModel:
        """Validate input data against the input schema."""
        try:
            return self.input_schema(**data)
        except Exception as e:
            raise ValueError(f"Input validation failed for {self.id}: {e}") from e
    
    def validate_output(self, data: Dict[str, Any]) -> BaseModel:
        """Validate output data against the output schema."""
        try:
            return self.output_schema(**data)
        except Exception as e:
            raise ValueError(f"Output validation failed for {self.id}: {e}") from e
    
    def execute(self, state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute the instruction with proper validation and error handling.
        
        Args:
            state: Current agent state
            **kwargs: Additional execution parameters
            
        Returns:
            Validated output data
        """
        # Extract input data from state
        input_data = state.get("user_state", {})
        
        # Validate input
        validated_input = self.validate_input(input_data)
        
        # Execute implementation
        try:
            result = self.implementation(validated_input, **kwargs)
            
            # Ensure result is a dictionary
            if not isinstance(result, dict):
                result = {"result": result}
                
            # Validate output
            validated_output = self.validate_output(result)
            
            return validated_output.model_dump()
            
        except Exception as e:
            raise RuntimeError(f"Instruction execution failed for {self.id}: {e}") from e


class InstructionResult(BaseModel):
    """Result of instruction execution with metadata."""
    
    instruction_id: str
    instruction_type: InstructionType
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float
    tokens_used: Optional[int] = None
    retry_count: int = 0
    
    class Config:
        arbitrary_types_allowed = True
