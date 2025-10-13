"""Migration assistant CLI tool for converting LangGraph projects to ArbiterOS."""

import os
import ast
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn


console = Console()


class LangGraphAnalyzer:
    """Analyzer for LangGraph projects."""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.python_files: List[Path] = []
        self.graph_definitions: List[Dict[str, Any]] = []
        self.node_functions: List[Dict[str, Any]] = []
        
    def analyze_project(self) -> Dict[str, Any]:
        """Analyze the LangGraph project."""
        console.print("🔍 Analyzing LangGraph project...")
        
        # Find Python files
        self._find_python_files()
        
        # Analyze each file
        for file_path in self.python_files:
            self._analyze_file(file_path)
        
        return {
            "project_path": str(self.project_path),
            "python_files": [str(f) for f in self.python_files],
            "graph_definitions": self.graph_definitions,
            "node_functions": self.node_functions,
            "recommendations": self._generate_recommendations()
        }
    
    def _find_python_files(self) -> None:
        """Find all Python files in the project."""
        for file_path in self.project_path.rglob("*.py"):
            if not file_path.name.startswith("."):
                self.python_files.append(file_path)
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self._analyze_function(node, file_path)
                elif isinstance(node, ast.ClassDef):
                    self._analyze_class(node, file_path)
                    
        except Exception as e:
            console.print(f"⚠️  Error analyzing {file_path}: {e}")
    
    def _analyze_function(self, node: ast.FunctionDef, file_path: Path) -> None:
        """Analyze a function definition."""
        # Check if this looks like a LangGraph node function
        if self._is_langgraph_node(node):
            self.node_functions.append({
                "name": node.name,
                "file": str(file_path),
                "line": node.lineno,
                "type": self._classify_node_type(node),
                "dependencies": self._extract_dependencies(node)
            })
    
    def _analyze_class(self, node: ast.ClassDef, file_path: Path) -> None:
        """Analyze a class definition."""
        # Check if this looks like a StateGraph definition
        if self._is_state_graph_class(node):
            self.graph_definitions.append({
                "name": node.name,
                "file": str(file_path),
                "line": node.lineno,
                "methods": [method.name for method in node.body if isinstance(method, ast.FunctionDef)]
            })
    
    def _is_langgraph_node(self, node: ast.FunctionDef) -> bool:
        """Check if a function looks like a LangGraph node."""
        # Look for common patterns
        if node.name.startswith("_"):
            return False
        
        # Check for state parameter
        args = [arg.arg for arg in node.args.args]
        if "state" in args or len(args) == 1:
            return True
        
        return False
    
    def _is_state_graph_class(self, node: ast.ClassDef) -> bool:
        """Check if a class looks like a StateGraph."""
        # Look for StateGraph in base classes or methods
        for base in node.bases:
            if isinstance(base, ast.Name) and "StateGraph" in base.id:
                return True
        
        # Look for common StateGraph methods
        method_names = [method.name for method in node.body if isinstance(method, ast.FunctionDef)]
        if any(name in method_names for name in ["add_node", "add_edge", "compile"]):
            return True
        
        return False
    
    def _classify_node_type(self, node: ast.FunctionDef) -> str:
        """Classify the type of node function."""
        name_lower = node.name.lower()
        
        if any(keyword in name_lower for keyword in ["generate", "create", "write"]):
            return "GENERATE"
        elif any(keyword in name_lower for keyword in ["call", "execute", "run", "tool"]):
            return "TOOL_CALL"
        elif any(keyword in name_lower for keyword in ["verify", "check", "validate"]):
            return "VERIFY"
        elif any(keyword in name_lower for keyword in ["fallback", "backup", "recover"]):
            return "FALLBACK"
        elif any(keyword in name_lower for keyword in ["compress", "summarize", "reduce"]):
            return "COMPRESS"
        else:
            return "UNKNOWN"
    
    def _extract_dependencies(self, node: ast.FunctionDef) -> List[str]:
        """Extract dependencies from a function."""
        dependencies = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    dependencies.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    dependencies.append(child.func.attr)
        
        return dependencies
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate migration recommendations."""
        recommendations = []
        
        # Check for missing governance
        if not any(node["type"] == "VERIFY" for node in self.node_functions):
            recommendations.append({
                "type": "missing_verification",
                "severity": "high",
                "message": "No verification nodes found. Consider adding VERIFY instructions.",
                "suggestion": "Add verification steps after GENERATE instructions"
            })
        
        # Check for direct GENERATE -> TOOL_CALL flows
        generate_nodes = [node for node in self.node_functions if node["type"] == "GENERATE"]
        tool_call_nodes = [node for node in self.node_functions if node["type"] == "TOOL_CALL"]
        
        if generate_nodes and tool_call_nodes and not any(node["type"] == "VERIFY" for node in self.node_functions):
            recommendations.append({
                "type": "unsafe_flow",
                "severity": "critical",
                "message": "Direct GENERATE -> TOOL_CALL flow detected without verification",
                "suggestion": "Add VERIFY instructions between GENERATE and TOOL_CALL"
            })
        
        # Check for missing fallback mechanisms
        if not any(node["type"] == "FALLBACK" for node in self.node_functions):
            recommendations.append({
                "type": "missing_fallback",
                "severity": "medium",
                "message": "No fallback mechanisms found",
                "suggestion": "Add FALLBACK instructions for error recovery"
            })
        
        return recommendations


class ArbiterOSGenerator:
    """Generator for ArbiterOS code."""
    
    def __init__(self, analysis: Dict[str, Any]):
        self.analysis = analysis
    
    def generate_migration_code(self) -> Dict[str, str]:
        """Generate ArbiterOS migration code."""
        generated_files = {}
        
        # Generate main ArbiterOS file
        generated_files["arbiteros_agent.py"] = self._generate_main_agent()
        
        # Generate policy configuration
        generated_files["policy_config.py"] = self._generate_policy_config()
        
        # Generate instruction bindings
        generated_files["instruction_bindings.py"] = self._generate_instruction_bindings()
        
        # Generate example usage
        generated_files["example_usage.py"] = self._generate_example_usage()
        
        return generated_files
    
    def _generate_main_agent(self) -> str:
        """Generate the main ArbiterOS agent file."""
        return '''"""
ArbiterOS Agent - Generated from LangGraph project.
"""

from arbiteros import ArbiterGraph, PolicyConfig, InstructionBinding, InstructionType
from instruction_bindings import get_instruction_bindings
from policy_config import get_policy_config


def create_arbiter_agent():
    """Create the ArbiterOS agent."""
    
    # Get policy configuration
    policy_config = get_policy_config()
    
    # Create ArbiterGraph
    arbiter_graph = ArbiterGraph(
        policy_config=policy_config,
        enable_observability=True
    )
    
    # Add instruction bindings
    bindings = get_instruction_bindings()
    for binding in bindings:
        arbiter_graph.add_instruction(binding)
    
    # Define execution flow
    # TODO: Define your execution flow based on your LangGraph structure
    # Example:
    # arbiter_graph.add_edge("generate_1", "verify_1")
    # arbiter_graph.add_edge("verify_1", "tool_call_1")
    
    # Set entry and exit points
    # TODO: Set your entry and exit points
    # Example:
    # arbiter_graph.set_entry_point("generate_1")
    # arbiter_graph.set_finish_point("tool_call_1")
    
    return arbiter_graph


if __name__ == "__main__":
    # Create and execute the agent
    agent = create_arbiter_agent()
    
    # Execute with initial state
    result = agent.execute({
        # TODO: Add your initial state here
    })
    
    print("Execution completed!")
    print(f"Final state: {result.get_state_summary()}")
'''
    
    def _generate_policy_config(self) -> str:
        """Generate policy configuration file."""
        return '''"""
Policy configuration for ArbiterOS agent.
"""

from arbiteros import PolicyConfig, PolicyRule, PolicyRuleType


def get_policy_config():
    """Get the policy configuration."""
    
    return PolicyConfig(
        policy_id="migrated_agent_policy",
        description="Policy for migrated LangGraph agent",
        rules=[
            PolicyRule(
                rule_id="semantic_safety_1",
                rule_type=PolicyRuleType.SEMANTIC_SAFETY,
                description="Ensure GENERATE is followed by VERIFY before TOOL_CALL",
                condition={
                    "allowed_flows": ["GENERATE->VERIFY->TOOL_CALL"]
                },
                action="INTERRUPT",
                severity="critical",
                applies_to=["TOOL_CALL"]
            ),
            PolicyRule(
                rule_id="content_length_1",
                rule_type=PolicyRuleType.CONTENT_AWARE,
                description="Limit content length",
                condition={
                    "max_length": 1000
                },
                action="FALLBACK",
                severity="warning",
                applies_to=["GENERATE"]
            ),
            PolicyRule(
                rule_id="resource_limit_1",
                rule_type=PolicyRuleType.RESOURCE_LIMIT,
                description="Limit token usage",
                condition={
                    "max_tokens": 1000
                },
                action="INTERRUPT",
                severity="error",
                applies_to=["GENERATE", "TOOL_CALL"]
            )
        ],
        max_tokens=1000,
        max_execution_time=60.0,
        strict_mode=True
    )
'''
    
    def _generate_instruction_bindings(self) -> str:
        """Generate instruction bindings file."""
        return '''"""
Instruction bindings for ArbiterOS agent.
"""

from typing import Dict, Any, List
from pydantic import BaseModel
from arbiteros import InstructionBinding, InstructionType


# TODO: Define your input/output schemas
class GenerateInput(BaseModel):
    prompt: str
    max_tokens: int = 100


class GenerateOutput(BaseModel):
    text: str
    tokens_used: int


class ToolCallInput(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]


class ToolCallOutput(BaseModel):
    result: Any
    success: bool


# TODO: Implement your instruction functions
def generate_instruction(state: GenerateInput) -> Dict[str, Any]:
    """Generate instruction implementation."""
    # TODO: Implement your generation logic
    return {
        "text": f"Generated response for: {state.prompt}",
        "tokens_used": len(state.prompt)
    }


def tool_call_instruction(state: ToolCallInput) -> Dict[str, Any]:
    """Tool call instruction implementation."""
    # TODO: Implement your tool call logic
    return {
        "result": f"Tool {state.tool_name} executed",
        "success": True
    }


def get_instruction_bindings() -> List[InstructionBinding]:
    """Get all instruction bindings."""
    
    return [
        InstructionBinding(
            id="generate_1",
            instruction_type=InstructionType.GENERATE,
            input_schema=GenerateInput,
            output_schema=GenerateOutput,
            implementation=generate_instruction,
            description="Generate text based on prompt",
            requires_verification=True,
            estimated_tokens=100
        ),
        InstructionBinding(
            id="tool_call_1",
            instruction_type=InstructionType.TOOL_CALL,
            input_schema=ToolCallInput,
            output_schema=ToolCallOutput,
            implementation=tool_call_instruction,
            description="Execute tool call",
            requires_verification=True
        )
        # TODO: Add more instruction bindings as needed
    ]
'''
    
    def _generate_example_usage(self) -> str:
        """Generate example usage file."""
        return '''"""
Example usage of the ArbiterOS agent.
"""

from arbiteros_agent import create_arbiter_agent


def main():
    """Main example function."""
    
    # Create the agent
    agent = create_arbiter_agent()
    
    # Execute with example state
    result = agent.execute({
        "prompt": "Hello, world!",
        "tool_name": "example_tool",
        "parameters": {"example": "value"}
    })
    
    print("Execution completed!")
    print(f"Final state: {result.get_state_summary()}")
    
    # Show execution trace
    trace = agent.get_execution_trace()
    print(f"Execution trace: {len(trace)} events")
    
    # Show trace summary
    summary = agent.get_trace_summary()
    print(f"Trace summary: {summary}")


if __name__ == "__main__":
    main()
'''


@click.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--output-dir', '-o', default='./arbiteros_migration', 
              help='Output directory for generated files')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def main(project_path: str, output_dir: str, verbose: bool):
    """ArbiterOS Migration Assistant - Convert LangGraph projects to ArbiterOS."""
    
    console.print(Panel.fit(
        "[bold blue]ArbiterOS Migration Assistant[/bold blue]\n"
        "Converting LangGraph projects to ArbiterOS governance",
        border_style="blue"
    ))
    
    # Analyze the project
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing project...", total=None)
        
        analyzer = LangGraphAnalyzer(project_path)
        analysis = analyzer.analyze_project()
        
        progress.update(task, description="Analysis complete!")
    
    # Display analysis results
    console.print("\n[bold green]Analysis Results:[/bold green]")
    
    # Create results table
    table = Table(title="Project Analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Python files", str(len(analysis["python_files"])))
    table.add_row("Graph definitions", str(len(analysis["graph_definitions"])))
    table.add_row("Node functions", str(len(analysis["node_functions"])))
    table.add_row("Recommendations", str(len(analysis["recommendations"])))
    
    console.print(table)
    
    # Display node functions
    if analysis["node_functions"]:
        console.print("\n[bold yellow]Node Functions Found:[/bold yellow]")
        for node in analysis["node_functions"]:
            console.print(f"  • {node['name']} ({node['type']}) - {node['file']}:{node['line']}")
    
    # Display recommendations
    if analysis["recommendations"]:
        console.print("\n[bold red]Migration Recommendations:[/bold red]")
        for rec in analysis["recommendations"]:
            severity_color = {
                "critical": "red",
                "high": "yellow", 
                "medium": "blue",
                "low": "green"
            }.get(rec["severity"], "white")
            
            console.print(f"  [{severity_color}]• {rec['message']}[/{severity_color}]")
            console.print(f"    Suggestion: {rec['suggestion']}")
    
    # Generate migration code
    console.print("\n[bold blue]Generating ArbiterOS code...[/bold blue]")
    
    generator = ArbiterOSGenerator(analysis)
    generated_files = generator.generate_migration_code()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Write generated files
    for filename, content in generated_files.items():
        file_path = output_path / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        console.print(f"  ✓ Generated {filename}")
    
    # Create requirements.txt
    requirements_content = """# ArbiterOS requirements
arbiteros-core>=0.1.0
langgraph>=0.2.0
langchain>=0.3.0
pydantic>=2.0.0
"""
    requirements_path = output_path / "requirements.txt"
    with open(requirements_path, 'w') as f:
        f.write(requirements_content)
    console.print("  ✓ Generated requirements.txt")
    
    # Create README
    readme_content = f"""# ArbiterOS Migration

This project has been migrated from LangGraph to ArbiterOS.

## Generated Files

- `arbiteros_agent.py` - Main ArbiterOS agent implementation
- `policy_config.py` - Policy configuration
- `instruction_bindings.py` - Instruction bindings
- `example_usage.py` - Example usage

## Usage

```python
from arbiteros_agent import create_arbiter_agent

# Create the agent
agent = create_arbiter_agent()

# Execute with initial state
result = agent.execute({{
    "prompt": "Your prompt here",
    "tool_name": "your_tool",
    "parameters": {{"key": "value"}}
}})

print("Execution completed!")
print(f"Final state: {{result.get_state_summary()}}")
```

## Next Steps

1. Review the generated code
2. Implement your instruction functions
3. Define your execution flow
4. Test the agent
5. Customize policies as needed

## Migration Notes

{len(analysis['recommendations'])} recommendations were generated during migration.
Please review and address them as needed.
"""
    
    readme_path = output_path / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    console.print("  ✓ Generated README.md")
    
    console.print(f"\n[bold green]Migration complete![/bold green]")
    console.print(f"Generated files in: {output_path.absolute()}")
    console.print(f"\nNext steps:")
    console.print(f"  1. Review the generated code")
    console.print(f"  2. Implement your instruction functions")
    console.print(f"  3. Define your execution flow")
    console.print(f"  4. Test the agent")


if __name__ == "__main__":
    main()
