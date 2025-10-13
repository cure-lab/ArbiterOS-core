# ArbiterOS-Core Installation Guide

## Quick Installation

```bash
# Install from PyPI (when available)
pip install arbiteros-core

# Or install from source
git clone https://github.com/arbiteros/arbiteros-core.git
cd arbiteros-core
pip install -e .
```

## Development Installation

```bash
# Clone the repository
git clone https://github.com/arbiteros/arbiteros-core.git
cd arbiteros-core

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Install example dependencies
pip install -e ".[examples]"
```

## Dependencies

### Core Dependencies
- Python 3.8+
- langgraph>=0.2.0
- langchain>=0.3.0
- pydantic>=2.0.0
- openai>=1.0.0

### Optional Dependencies
- redis>=5.0.0 (for persistence)
- opentelemetry-api>=1.20.0 (for observability)
- instructor>=1.0.0 (for structured output)

## Environment Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Environment Variables
```bash
# For OpenAI integration
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_BASE_URL="https://a.fe8.cn/v1"  # If using custom endpoint

# For observability (optional)
export JAEGER_ENDPOINT="http://localhost:14268"
```

## Quick Start

### 1. Basic Usage
```python
from arbiteros import ArbiterGraph, PolicyConfig, InstructionBinding, InstructionType
from pydantic import BaseModel

# Define your schemas
class Input(BaseModel):
    prompt: str

class Output(BaseModel):
    result: str

# Create policy
policy = PolicyConfig(
    policy_id="my_policy",
    description="My agent policy",
    rules=[]
)

# Create instruction
def my_instruction(state: Input) -> dict:
    return {"result": f"Processed: {state.prompt}"}

binding = InstructionBinding(
    id="my_instruction",
    instruction_type=InstructionType.GENERATE,
    input_schema=Input,
    output_schema=Output,
    implementation=my_instruction
)

# Create and run agent
agent = ArbiterGraph(policy_config=policy)
agent.add_instruction(binding)
agent.set_entry_point("my_instruction")
agent.set_finish_point("my_instruction")

result = agent.execute({"prompt": "Hello, world!"})
print(result.get_state_summary())
```

### 2. Run Examples
```bash
# Run the demo
python demo.py

# Run the simple agent example
python -m arbiteros.examples.simple_agent

# Run basic tests
python test_basic.py
```

### 3. Use Migration Assistant
```bash
# Convert a LangGraph project
arbiteros-assist /path/to/your/langgraph/project --output-dir ./arbiteros_migration
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Make sure you're in the right environment
   pip list | grep arbiteros
   ```

2. **OpenTelemetry Issues**
   ```bash
   # Install OpenTelemetry dependencies
   pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-jaeger
   ```

3. **Redis Connection Issues**
   ```bash
   # Install Redis
   pip install redis
   # Or use Docker
   docker run -d -p 6379:6379 redis:alpine
   ```

### Getting Help

- Check the [README.md](README.md) for detailed documentation
- Run `python demo.py` to see the system in action
- Check the examples in `arbiteros/examples/`
- Open an issue on GitHub for bugs or feature requests

## Next Steps

1. **Explore Examples**: Check out the examples in `arbiteros/examples/`
2. **Read Documentation**: See the full documentation in the README
3. **Try Migration**: Use the migration assistant to convert your LangGraph projects
4. **Customize Policies**: Create your own policy configurations
5. **Add Observability**: Set up Jaeger for distributed tracing

## Support

- GitHub Issues: https://github.com/arbiteros/arbiteros-core/issues
- Documentation: https://arbiteros.dev/docs
- Community: https://github.com/arbiteros/arbiteros-core/discussions
