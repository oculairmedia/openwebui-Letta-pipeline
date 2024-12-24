# OpenWebUI-Letta Pipeline

This pipeline provides integration between Letta agents and OpenWebUI models. It enables you to use Letta's agent capabilities while leveraging OpenWebUI's model infrastructure and tools.

## Overview

This pipeline connects a Letta agent to an OpenWebUI "model". The integration:
- Allows Letta agents to use OpenWebUI's model endpoints
- Supports OpenWebUI tool usage functionality through the enhanced pipeline version
- Focuses on providing a clean interface between Letta's agent capabilities and OpenWebUI's features

## Pipeline Versions

1. `lettapipeline.py` - Basic version that connects Letta agents to OpenWebUI models
2. `lettapipeline_with_tools.py` - Enhanced version that adds support for OpenWebUI tools

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