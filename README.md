# OpenWebUI-Letta Pipeline

This pipeline provides integration between Letta agents and OpenWebUI models, allowing OpenWebUI tools to enhance Letta's responses.

## Overview

This pipeline connects OpenWebUI and Letta in a way that:
- Uses OpenWebUI's existing tools (like web search)
- Passes tool results to Letta for processing
- Returns Letta's enhanced responses back to OpenWebUI
- Maintains a seamless conversation flow

## Pipeline Versions

1. `lettapipeline.py` - Basic version that connects Letta agents to OpenWebUI models
2. `lettapipeline_with_openwebui_tools.py` - Enhanced version that integrates OpenWebUI's tool results with Letta

## How It Works

1. OpenWebUI executes its tools (e.g., web search)
2. Tool results are passed to the pipeline in the request body
3. Pipeline sends tool results to Letta as system messages
4. Letta processes the tool results along with the user's message
5. Pipeline returns Letta's response to OpenWebUI

## Repository Structure

- `lettapipeline.py`: The main pipeline implementation for connecting Letta agents to OpenWebUI
- `letta examples/`: Collection of example Letta agent implementations and usage patterns
- `openwebui pipeline examples/`: Various OpenWebUI pipeline examples including:
  - Filters
  - Integration patterns
  - Provider implementations
  - RAG implementations

## Usage

The pipeline serves as a bridge between Letta's agent ecosystem and OpenWebUI's model infrastructure. This allows you to:
1. Use Letta's advanced agent capabilities
2. Connect to models served through OpenWebUI
3. Maintain separation of concerns between agent logic and model serving

## Examples

You can find extensive examples in both the `letta examples` and `openwebui pipeline examples` directories, demonstrating various implementation patterns and use cases.