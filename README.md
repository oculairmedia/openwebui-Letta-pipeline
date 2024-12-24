# OpenWebUI-Letta Pipeline

This pipeline provides integration between Letta agents and OpenWebUI models. It enables you to use Letta's agent capabilities while leveraging OpenWebUI's model infrastructure.

## Overview

This pipeline connects a Letta agent to an OpenWebUI "model". It's important to note that this integration:
- Allows Letta agents to use OpenWebUI's model endpoints
- Does NOT include OpenWebUI tool usage functionality
- Focuses on providing a clean interface between Letta's agent capabilities and OpenWebUI's model serving

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