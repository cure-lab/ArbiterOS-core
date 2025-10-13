"""Observability and tracing for ArbiterOS."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
import json
import logging

# OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.instrumentation.auto_instrumentation import sitecustomize
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    # Create dummy classes for when OpenTelemetry is not available
    class trace:
        class Tracer:
            def start_span(self, *args, **kwargs):
                return DummySpan()
        def get_tracer(self, *args, **kwargs):
            return self.Tracer()
    
    class DummySpan:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def set_attribute(self, *args, **kwargs):
            pass
        def set_status(self, *args, **kwargs):
            pass
        def add_event(self, *args, **kwargs):
            pass
        def end(self, *args, **kwargs):
            pass


class TraceEvent(BaseModel):
    """Individual trace event."""
    
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any] = Field(default_factory=dict)
    instruction_id: Optional[str] = Field(default=None)
    execution_id: Optional[str] = Field(default=None)


class FlightDataRecorder:
    """
    Flight Data Recorder for ArbiterOS - provides comprehensive execution tracing.
    
    This implements the "Flight Data Recorder" concept from the ArbiterOS paper,
    enabling time-travel debugging and comprehensive audit trails.
    """
    
    def __init__(self, enable_otel: bool = True, jaeger_endpoint: Optional[str] = None):
        """
        Initialize the Flight Data Recorder.
        
        Args:
            enable_otel: Whether to enable OpenTelemetry tracing
            jaeger_endpoint: Jaeger endpoint for distributed tracing
        """
        self.enable_otel = enable_otel and OTEL_AVAILABLE
        self.jaeger_endpoint = jaeger_endpoint
        self.traces: List[TraceEvent] = []
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenTelemetry if enabled
        if self.enable_otel:
            self._setup_otel()
        else:
            self.logger.warning("OpenTelemetry not available, using basic tracing")
    
    def _setup_otel(self) -> None:
        """Set up OpenTelemetry tracing."""
        try:
            # Create resource
            resource = Resource.create({
                "service.name": "arbiteros-core",
                "service.version": "0.1.0"
            })
            
            # Set up tracer provider
            trace.set_tracer_provider(TracerProvider(resource=resource))
            tracer = trace.get_tracer(__name__)
            
            # Set up Jaeger exporter if endpoint provided
            if self.jaeger_endpoint:
                jaeger_exporter = JaegerExporter(
                    agent_host_name="localhost",
                    agent_port=14268,
                )
                span_processor = BatchSpanProcessor(jaeger_exporter)
                trace.get_tracer_provider().add_span_processor(span_processor)
            
            self.tracer = tracer
            self.logger.info("OpenTelemetry tracing initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenTelemetry: {e}")
            self.enable_otel = False
    
    def start_trace(self, name: str, execution_id: str, **attributes) -> Any:
        """
        Start a new trace span.
        
        Args:
            name: Name of the trace span
            execution_id: Unique execution identifier
            **attributes: Additional span attributes
            
        Returns:
            Trace span object
        """
        if self.enable_otel:
            span = self.tracer.start_span(name)
            span.set_attribute("execution_id", execution_id)
            for key, value in attributes.items():
                span.set_attribute(key, value)
            return span
        else:
            # Return a dummy span for basic tracing
            return DummySpan()
    
    def record_event(
        self, 
        event_type: str, 
        data: Dict[str, Any], 
        instruction_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> None:
        """
        Record a trace event.
        
        Args:
            event_type: Type of event (e.g., "instruction_start", "policy_violation")
            data: Event data
            instruction_id: Associated instruction ID
            execution_id: Associated execution ID
        """
        event = TraceEvent(
            event_type=event_type,
            data=data,
            instruction_id=instruction_id,
            execution_id=execution_id
        )
        
        self.traces.append(event)
        
        # Log the event
        self.logger.info(f"Trace event: {event_type} - {data}")
    
    def record_instruction_start(
        self, 
        instruction_id: str, 
        instruction_type: str, 
        execution_id: str
    ) -> None:
        """Record the start of an instruction execution."""
        self.record_event(
            "instruction_start",
            {
                "instruction_id": instruction_id,
                "instruction_type": instruction_type,
                "status": "started"
            },
            instruction_id=instruction_id,
            execution_id=execution_id
        )
    
    def record_instruction_end(
        self, 
        instruction_id: str, 
        success: bool, 
        execution_time: float,
        tokens_used: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """Record the end of an instruction execution."""
        data = {
            "instruction_id": instruction_id,
            "status": "completed" if success else "failed",
            "execution_time": execution_time
        }
        
        if tokens_used is not None:
            data["tokens_used"] = tokens_used
        
        if error:
            data["error"] = error
        
        self.record_event(
            "instruction_end",
            data,
            instruction_id=instruction_id
        )
    
    def record_policy_evaluation(
        self, 
        instruction_id: str, 
        rule_results: List[Dict[str, Any]],
        execution_id: str
    ) -> None:
        """Record policy evaluation results."""
        self.record_event(
            "policy_evaluation",
            {
                "instruction_id": instruction_id,
                "rule_results": rule_results,
                "total_rules": len(rule_results),
                "violations": len([r for r in rule_results if not r.get("passed", True)])
            },
            instruction_id=instruction_id,
            execution_id=execution_id
        )
    
    def record_policy_violation(
        self, 
        instruction_id: str, 
        violation: Dict[str, Any],
        execution_id: str
    ) -> None:
        """Record a policy violation."""
        self.record_event(
            "policy_violation",
            {
                "instruction_id": instruction_id,
                "violation": violation,
                "severity": violation.get("severity", "warning")
            },
            instruction_id=instruction_id,
            execution_id=execution_id
        )
    
    def record_arbiter_decision(
        self, 
        instruction_id: str, 
        decision: str, 
        reason: str,
        execution_id: str
    ) -> None:
        """Record an arbiter routing decision."""
        self.record_event(
            "arbiter_decision",
            {
                "instruction_id": instruction_id,
                "decision": decision,
                "reason": reason
            },
            instruction_id=instruction_id,
            execution_id=execution_id
        )
    
    def record_state_transition(
        self, 
        from_state: str, 
        to_state: str, 
        execution_id: str
    ) -> None:
        """Record a state transition."""
        self.record_event(
            "state_transition",
            {
                "from_state": from_state,
                "to_state": to_state
            },
            execution_id=execution_id
        )
    
    def record_error(
        self, 
        instruction_id: str, 
        error: str, 
        error_type: str,
        execution_id: str
    ) -> None:
        """Record an error."""
        self.record_event(
            "error",
            {
                "instruction_id": instruction_id,
                "error": error,
                "error_type": error_type
            },
            instruction_id=instruction_id,
            execution_id=execution_id
        )
    
    def record_fallback_triggered(
        self, 
        instruction_id: str, 
        reason: str,
        execution_id: str
    ) -> None:
        """Record a fallback mechanism being triggered."""
        self.record_event(
            "fallback_triggered",
            {
                "instruction_id": instruction_id,
                "reason": reason
            },
            instruction_id=instruction_id,
            execution_id=execution_id
        )
    
    def record_interrupt(
        self, 
        instruction_id: str, 
        reason: str,
        execution_id: str
    ) -> None:
        """Record an interrupt."""
        self.record_event(
            "interrupt",
            {
                "instruction_id": instruction_id,
                "reason": reason
            },
            instruction_id=instruction_id,
            execution_id=execution_id
        )
    
    def get_execution_trace(self, execution_id: str) -> List[TraceEvent]:
        """Get the complete execution trace for a specific execution."""
        return [
            event for event in self.traces 
            if event.execution_id == execution_id
        ]
    
    def get_instruction_trace(self, instruction_id: str) -> List[TraceEvent]:
        """Get the trace for a specific instruction."""
        return [
            event for event in self.traces 
            if event.instruction_id == instruction_id
        ]
    
    def get_trace_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get a summary of the execution trace."""
        events = self.get_execution_trace(execution_id)
        
        summary = {
            "execution_id": execution_id,
            "total_events": len(events),
            "event_types": {},
            "instructions": set(),
            "errors": [],
            "policy_violations": [],
            "fallbacks": [],
            "interrupts": []
        }
        
        for event in events:
            # Count event types
            event_type = event.event_type
            summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1
            
            # Track instructions
            if event.instruction_id:
                summary["instructions"].add(event.instruction_id)
            
            # Categorize events
            if event_type == "error":
                summary["errors"].append(event.data)
            elif event_type == "policy_violation":
                summary["policy_violations"].append(event.data)
            elif event_type == "fallback_triggered":
                summary["fallbacks"].append(event.data)
            elif event_type == "interrupt":
                summary["interrupts"].append(event.data)
        
        # Convert set to list for JSON serialization
        summary["instructions"] = list(summary["instructions"])
        
        return summary
    
    def export_trace(self, execution_id: str, format: str = "json") -> str:
        """
        Export the execution trace in the specified format.
        
        Args:
            execution_id: Execution ID to export
            format: Export format ("json", "text")
            
        Returns:
            Exported trace data
        """
        events = self.get_execution_trace(execution_id)
        
        if format == "json":
            return json.dumps([event.model_dump() for event in events], default=str, indent=2)
        elif format == "text":
            lines = []
            for event in events:
                lines.append(f"[{event.timestamp}] {event.event_type}: {event.data}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def clear_traces(self) -> None:
        """Clear all stored traces."""
        self.traces.clear()
        self.logger.info("All traces cleared")
