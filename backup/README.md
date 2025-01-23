# OpenWebUI-Letta Pipeline

This pipeline provides integration between Letta agents and OpenWebUI models, with proper system message handling for tool results. It offers both synchronous and asynchronous implementations to suit different deployment needs.

## Overview

This pipeline connects OpenWebUI and Letta in a way that:
- Captures OpenWebUI context and tool results
- Formats everything as proper system messages for Letta
- Preserves the full context of tool interactions
- Enables informed responses based on tool outputs
- Supports both synchronous and asynchronous operations

## Pipeline Implementations

### Synchronous Pipeline (`lettapipeline.py`)
- Uses urllib3 for HTTP requests
- Suitable for basic integrations and sequential processing
- Blocking I/O operations
- Simple to integrate with existing synchronous code

### Asynchronous Pipeline (`async_lettapipeline.py`)
- Uses httpx for async HTTP requests
- Ideal for high-concurrency scenarios
- Non-blocking I/O operations
- Better performance in async web frameworks (FastAPI, aiohttp)
- Efficient handling of multiple concurrent requests

## How It Works

1. OpenWebUI executes its tools (e.g., web search)
2. Tool results are passed to the pipeline in the request body
3. Pipeline sends tool results to Letta as system messages
4. Letta processes the tool results along with the user's message
5. Pipeline returns Letta's response to OpenWebUI

## Repository Structure

- `lettapipeline.py`: Synchronous pipeline implementation
- `async_lettapipeline.py`: Asynchronous pipeline implementation
- `letta examples/`: Collection of example Letta agent implementations
- `openwebui pipeline examples/`: Various OpenWebUI pipeline examples including:
  - Filters
  - Integration patterns
  - Provider implementations
  - RAG implementations

## Usage

### Synchronous Pipeline
```python
from lettapipeline import Pipeline

pipeline = Pipeline()
result = pipeline.pipe(
    user_message="Hello",
    model_id="your_model",
    messages=[],
    body={}
)
print(result)
```

### Asynchronous Pipeline
```python
import asyncio
from async_lettapipeline import Pipeline

async def main():
    pipeline = Pipeline()
    result = await pipeline.pipe(
        user_message="Hello",
        model_id="your_model",
        messages=[],
        body={}
    )
    print(result)

asyncio.run(main())
```

## Dependencies

### Synchronous Pipeline
- pydantic
- urllib3

### Asynchronous Pipeline
- pydantic
- httpx

## Examples

You can find extensive examples in both the `letta examples` and `openwebui pipeline examples` directories, demonstrating various implementation patterns and use cases.

## Choosing Between Sync and Async

Choose the synchronous pipeline when:
- You have a simple, sequential processing workflow
- You're integrating with existing synchronous code
- You don't need to handle multiple concurrent requests
- You want minimal dependencies

Choose the asynchronous pipeline when:
- You need to handle multiple concurrent requests efficiently
- You're using an async web framework (FastAPI, aiohttp)
- You want better performance under high load
- You're integrating with other async services

## Contributing

Contributions are welcome! Please feel free to submit pull requests with improvements to either the synchronous or asynchronous implementations.