# Async Letta Chat Pipeline

This document describes the asynchronous pipeline (`async_lettapipeline.py`) used for handling chat-based messaging with Letta's agent service. It provides real-time streaming through HTTP and can be adapted to SSE or WebSocket interfaces.

## Overview

- Uses `httpx` for async HTTP requests to the Letta agent service.
- Processes messages in streaming fashion, checking for user or system content via the `_process_messages` method.
- Supports naming the pipeline and reading basic config such as `base_url` and `agent_id` from the `Valves` model.
- Allows pipeline customization via `inlet` and `outlet` methods for pre- and post-processing messages.

## Key Components

1. **`StreamEvent`**  
   - A Pydantic model representing a generic streaming event.
   - Contains event `type` and `data` (a dictionary of fields needed for each event in the stream).

2. **`Pipeline`**  
   - Main class that initializes configuration and contains logic for streaming.
   - Key methods:
     - `pipe(...)`: Orchestrates the streaming process from incoming messages to the final output.
     - `_process_messages(...)`: Extracts message content from messages containing `tool_call_message`.
     - `get_client(...)`: Produces an `httpx.AsyncClient` configured with SSL disabled (for local/TLS use).
     - `on_startup(...)`, `on_shutdown(...)`: Lifecycle hooks for initialization and cleanup.

## Usage

1. **Instantiate the Pipeline**  
   ```python
   from async_lettapipeline import Pipeline
   pipeline = Pipeline()
   ```

2. **Invoke the Streaming Process**  
   You can then call `pipeline.pipe(...)` with the required parameters (e.g. `user_message`, `model_id`, existing messages, etc.), and it returns an async generator yielding streaming JSON events.

3. **Configuration**  
   - Modify `base_url` in `valves` if using a different agent endpoint.
   - Adjust `agent_id` to match your specific agent.

## Error Handling

- The pipeline raises `LettaError` for internal exceptions.
- HTTP and JSON decode errors are caught and returned as `chat:error` events in the stream.

## Future Updates

- Extending the `_extract_message_content` to accommodate other message types.
- Customizing polling intervals or switching from polling to push-based events.
- Adding more robust error recovery logic in `_process_messages`.