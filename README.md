# Python Code Generator API

A FastAPI-based service that uses LiteLLM to generate Python code based on user prompts.

## Features

- Async endpoint for code generation
- Supports multiple LLM models through LiteLLM
- Configurable parameters (model, max_tokens, temperature)
- Clean API responses with Pydantic models

## Installation

```bash
# Install dependencies using uv
uv sync

# Or using pip
pip install -e .
```

## Environment Setup

### Using .env file (Recommended)

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API key(s):
```bash
# For OpenAI
OPENAI_API_KEY=your-api-key

# For Anthropic (Claude)
ANTHROPIC_API_KEY=your-api-key

# For other providers, see LiteLLM documentation
```

The application will automatically load environment variables from the `.env` file.

### Using environment variables directly

Alternatively, you can set environment variables in your shell:

```bash
# For OpenAI
export OPENAI_API_KEY="your-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-api-key"

# For other providers, see LiteLLM documentation
```

## Running the Server

```bash
# Run with Python
uv run main.py

# Or with uvicorn directly
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### POST /generate-code

Generate Python code based on a prompt.

**Request Body:**
```json
{
  "prompt": "Create a function to calculate fibonacci numbers",
  "model": "gpt-3.5-turbo",
  "max_tokens": 1000,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "generated_code": "def fibonacci(n):\n    ...",
  "model_used": "gpt-3.5-turbo"
}
```

### GET /

Root endpoint - returns API status.

### GET /health

Health check endpoint.

## Example Usage

### Using curl

```bash
curl -X POST "http://localhost:8000/generate-code" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a function that sorts a list of dictionaries by a specific key",
    "model": "gpt-3.5-turbo",
    "max_tokens": 500
  }'
```

### Using Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/generate-code",
    json={
        "prompt": "Create a class for a binary search tree with insert and search methods",
        "model": "gpt-3.5-turbo",
        "temperature": 0.5
    }
)

print(response.json()["generated_code"])
```

## Supported Models

LiteLLM supports 100+ models. Some examples:
- `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo` (OpenAI)
- `claude-3-opus-20240229`, `claude-3-sonnet-20240229` (Anthropic)
- `command-nightly` (Cohere)
- `gemini/gemini-pro` (Google)

See [LiteLLM documentation](https://docs.litellm.ai/docs/providers) for the full list.

## Configuration

You can customize the default model and parameters by modifying the `CodeGenerationRequest` model in [main.py](main.py).
