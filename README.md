# OpenWebUI-Letta Pipeline

This pipeline provides integration between Letta agents and OpenWebUI models, with proper system message handling and streaming support.

## Overview

This pipeline connects OpenWebUI and Letta in a way that:
- Provides both streaming and non-streaming responses
- Handles async communication with Letta agents
- Formats messages in OpenAI-compatible format
- Supports proper error handling and retries

## API Integration Details

### OpenWebUI Integration

The pipeline implements the OpenWebUI chat completion API:

```python
POST /chat/completions
{
    "messages": [{"role": "user", "content": "..."}],
    "model": "lettapipeline",
    "stream": true/false
}
```

Response format follows OpenAI's specification:
- Non-streaming: Single JSON response
- Streaming: Server-sent events with chunks

### Letta Integration

The pipeline uses Letta's Python client:

```python
from letta import create_client

client = create_client(base_url="http://...")
response = await client.send_message(
    agent_id="...",
    message="...",
    role="user"
)
```

Key features:
- Async communication
- Message history tracking
- Tool call handling

## Pipeline Implementation

The pipeline is implemented as an async Python class with these key methods:

1. `async def pipe(...)`: Main entry point handling both streaming and non-streaming
2. `async def get_response_message(...)`: Gets agent responses with retries
3. `async def on_startup/shutdown(...)`: Lifecycle management
4. `async def on_valves_updated(...)`: Configuration updates

### Streaming Support

For streaming responses, the pipeline:
1. Yields each character as a separate chunk
2. Follows OpenAI's streaming format
3. Handles proper chunk formatting
4. Sends final chunk with finish_reason

### Error Handling

The pipeline implements:
1. Retries for message retrieval
2. Exception catching and reporting
3. Proper error response formatting
4. Logging of error conditions

## Configuration

The pipeline uses a Valves class for configuration:

```python
class Valves(BaseModel):
    base_url: str = "http://..."
    agent_id: str = "..."
```

Configuration can be updated at runtime through the valves API.

## Usage

1. Install requirements:
```bash
pip install pydantic aiohttp letta
```

2. Deploy the pipeline:
```bash
# Upload pipeline
curl -X POST -H "Authorization: Bearer ..." -F "file=@lettapipeline.py" http://.../pipelines/upload

# Reload pipelines
curl -X POST -H "Authorization: Bearer ..." http://.../pipelines/reload
```

3. Use the API:
```bash
# Non-streaming
curl -X POST -H "Authorization: Bearer ..." -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "..."}], "model": "lettapipeline", "stream": false}' \
     http://.../chat/completions

# Streaming
curl -X POST -H "Authorization: Bearer ..." -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "..."}], "model": "lettapipeline", "stream": true}' \
     http://.../chat/completions
```

## Development

Key areas for future development:

1. Message History
- Implement proper conversation history tracking
- Add support for system messages
- Handle context windows

2. Tool Integration
- Add support for OpenWebUI tools
- Implement tool result formatting
- Handle async tool execution

3. Performance
- Add caching layer
- Implement connection pooling
- Add request batching

4. Monitoring
- Add metrics collection
- Implement proper logging
- Add tracing support

## Repository Structure

- `lettapipeline.py`: Main pipeline implementation
- `examples/`: Example implementations and usage patterns
- `tests/`: Test suite
- `docs/`: Additional documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details