# A2A Summarization Agent

A Cloud Foundry application that wraps the text summarization logic from **Notebook-Lab4** with **A2A (Agent-to-Agent) protocol**, making it accessible as a network-accessible agent.

## Overview

This application demonstrates how to:
1. Extract core logic from a Jupyter notebook (Lab4 summarization)
2. Wrap it with Google's A2A protocol using the A2A SDK
3. Deploy it as a standalone Cloud Foundry application
4. Interact with it via A2A JSON-RPC protocol

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    A2A Client                          │
│              (JSON-RPC Requests)                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              A2A Server (app.py)                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Request Handler (DefaultRequestHandler)        │   │
│  │  - Processes JSON-RPC requests                 │   │
│  │  - Manages task lifecycle                       │   │
│  └──────────────┬──────────────────────────────────┘   │
│                 │                                        │
│                 ▼                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Agent Executor (SummarizationAgentExecutor)   │   │
│  │  - Wraps summarization logic                    │   │
│  │  - Publishes task updates                       │   │
│  └──────────────┬──────────────────────────────────┘   │
└─────────────────┼──────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│        Summarizer Module (summarizer.py)                │
│  ┌─────────────────────────────────────────────────┐   │
│  │  FROM NOTEBOOK: Lab4 Logic                      │   │
│  │  - LLMChain setup                               │   │
│  │  - Prompt template                              │   │
│  │  - Summarization execution                      │   │
│  └──────────────┬──────────────────────────────────┘   │
└─────────────────┼──────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│         Cloud Foundry Services                          │
│  - tanzu-gpt-oss-120b (GenAI LLM service)              │
└─────────────────────────────────────────────────────────┘
```

## Code Structure

### File Organization

```
cf-jupyterlab-to-a2a/
├── app.py                    # A2A server and Agent Executor (A2A wrapper code)
├── summarizer.py             # Core summarization logic (from notebook)
├── cfutils/
│   ├── __init__.py
│   └── cfgenai.py            # CFGenAIService utility (from workshop)
├── pyproject.toml            # Python dependencies
├── manifest.yml              # Cloud Foundry deployment manifest
├── runtime.txt               # Python version specification
└── README.md                 # This file
```

### Code Comments

The code is extensively commented to show:
- **`# FROM NOTEBOOK:`** - Code directly extracted from Notebook-Lab4
- **`# A2A WRAPPER:`** - Code added to wrap notebook logic with A2A protocol

## Prerequisites

1. **Cloud Foundry CLI** installed and configured
2. **Cloud Foundry account** with access to:
   - `tanzu-gpt-oss-120b` service (GenAI LLM service)
3. **Python 3.11+** (for local development/testing)

## Deployment

### 1. Deploy to Cloud Foundry

```bash
cd cf-jupyterlab-to-a2a
cf push
```

The application will:
- Use the `uv-buildpack` to install dependencies
- Start the A2A server on port 8080 (Cloud Foundry sets PORT automatically)
- Be accessible at: `https://cf-summarization-a2a.<your-domain>`

### 2. Verify Deployment

```bash
# Check app status
cf apps

# View logs
cf logs cf-summarization-a2a --recent
```

## Usage

### 1. View Agent Card

The Agent Card describes the agent's capabilities and is available at the well-known endpoint:

```bash
# Get the app URL
APP_URL=$(cf app cf-summarization-a2a | grep "urls:" | awk '{print $2}')

# View the Agent Card
curl -s "https://${APP_URL}/.well-known/agent.json" | jq
```

**Expected Output:**
```json
{
  "name": "Text Summarization Agent",
  "description": "A2A agent that summarizes text using LangChain and OpenAI-compatible LLM endpoints",
  "url": "https://cf-summarization-a2a.<domain>",
  "version": "1.0.0",
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "capabilities": {
    "streaming": true
  },
  "skills": [
    {
      "id": "text-summarization",
      "name": "Text Summarization",
      "description": "Summarizes input text using LLM, producing concise summaries while preserving key information",
      "tags": ["summarization", "text-processing", "llm"]
    }
  ]
}
```

### 2. Trigger Summarization (Streaming)

Send a summarization request using A2A JSON-RPC protocol:

```bash
# Set your app URL
APP_URL="https://cf-summarization-a2a.<your-domain>"

# Send a summarization request with streaming
curl --location "${APP_URL}/" \
  --header 'Content-Type: application/json' \
  --data '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/stream",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "Cloud Foundry is an open-source platform-as-a-service (PaaS) that provides a way to deploy and scale applications. It supports multiple programming languages and frameworks, including Java, Node.js, Python, and Ruby. Cloud Foundry abstracts away infrastructure management, allowing developers to focus on writing code. The platform handles application lifecycle management, including deployment, scaling, and health monitoring. It also provides service integration capabilities, allowing applications to easily connect to databases, message queues, and other services through service bindings."
          }
        ],
        "messageId": "unique-message-id-123"
      },
      "metadata": {}
    }
  }'
```

**Expected Response (Streaming):**

The response will come in multiple chunks as the agent processes the request:

```json
// Stream 1: Task created
{
  "id": 1,
  "jsonrpc": "2.0",
  "result": {
    "contextId": "abc-123-def",
    "history": [...],
    "id": "task-456",
    "kind": "task",
    "status": {
      "state": "submitted"
    }
  }
}

// Stream 2: Processing started
{
  "id": 1,
  "jsonrpc": "2.0",
  "result": {
    "contextId": "abc-123-def",
    "final": false,
    "kind": "status-update",
    "status": {
      "message": {
        "parts": [{"kind": "text", "text": "Processing your text for summarization..."}],
        "role": "agent"
      },
      "state": "working"
    },
    "taskId": "task-456"
  }
}

// Stream 3: Summary completed
{
  "id": 1,
  "jsonrpc": "2.0",
  "result": {
    "contextId": "abc-123-def",
    "final": true,
    "kind": "status-update",
    "status": {
      "message": {
        "parts": [{
          "kind": "text",
          "text": "Cloud Foundry is an open-source PaaS platform that enables developers to deploy and scale applications across multiple programming languages. It simplifies infrastructure management by handling deployment, scaling, and health monitoring, while allowing developers to focus on coding. The platform also offers service integration for databases, message queues, and other services."
        }],
        "role": "agent"
      },
      "state": "completed"
    },
    "taskId": "task-456"
  }
}
```

### 3. Trigger Summarization (Non-Streaming)

For shorter tasks, you can use `message/send` instead of `message/stream`:

```bash
curl --location "${APP_URL}/" \
  --header 'Content-Type: application/json' \
  --data '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "Summarize this: Python is a high-level programming language known for its simplicity and readability."
          }
        ],
        "messageId": "message-id-456"
      },
      "metadata": {}
    }
  }'
```

This will return the final result directly without streaming updates.

## Testing Locally (Optional)

You can test the application locally before deploying:

```bash
# Install dependencies locally (requires uv)
uv sync

# Set environment variables (simulate Cloud Foundry)
export PORT=8080
export VCAP_SERVICES='{"user-provided":[...]}'  # Your service bindings

# Run the server
uv run python app.py
```

Then test the agent card:
```bash
curl http://localhost:8080/.well-known/agent.json | jq
```

## Code Breakdown

### What Comes from Notebook

The following code is directly extracted from **Notebook-Lab4**:

1. **Service Setup** (`summarizer.py` lines 30-40)
   - CFGenAIService initialization
   - Model listing and credential construction

2. **LLM Initialization** (`summarizer.py` lines 42-54)
   - httpx client setup
   - ChatOpenAI initialization

3. **Prompt Template** (`summarizer.py` lines 56-68)
   - The summarization prompt template

4. **Chain Creation** (`summarizer.py` lines 70-76)
   - LLMChain creation with LLM and prompt

5. **Summarization Call** (`summarizer.py` lines 88-92)
   - The `chain.predict(input=text)` call

### What's Added for A2A

The following code wraps the notebook logic with A2A protocol:

1. **Agent Skill Definition** (`app.py` lines 24-29)
   - Defines what the agent can do

2. **Agent Card** (`app.py` lines 35-57)
   - Describes agent identity and capabilities

3. **Agent Executor** (`app.py` lines 63-145)
   - Bridges A2A protocol with summarization logic
   - Handles task lifecycle and event publishing

4. **Request Handler** (`app.py` lines 151-156)
   - Processes A2A JSON-RPC requests

5. **Server Setup** (`app.py` lines 162-190)
   - Creates and configures the A2A Starlette application

## Troubleshooting

### Import Errors (a2a.server.request_handler not found)

If you see `ModuleNotFoundError: No module named 'a2a.server.request_handler'`, the a2a-sdk package structure may differ from expected. Try:

1. **Check the installed a2a-sdk version:**
   ```bash
   cf ssh cf-summarization-a2a
   uv pip list | grep a2a
   ````

2. **Update pyproject.toml** with a specific version:
   ```toml
   "a2a-sdk==0.1.0",  # Use specific version
   ```

3. **Check A2A SDK documentation** for the correct import paths for your version:
   - [A2A Python Tutorial](https://google.github.io/A2A/tutorials/python/1-introduction/)

The code includes fallback import attempts that try multiple paths automatically.

### Agent Card Not Accessible

```bash
# Check if the app is running
cf apps

# Check logs for errors
cf logs cf-summarization-a2a --recent

# Verify the endpoint
curl -v https://<your-app-url>/.well-known/agent.json
```

### Service Binding Issues

```bash
# List services bound to the app
cf services

# Check service bindings
cf app cf-summarization-a2a | grep "bound services"

# Verify VCAP_SERVICES
cf env cf-summarization-a2a | grep VCAP_SERVICES
```

### Summarization Fails

Check the logs for:
- LLM service connectivity issues
- Model availability
- Authentication errors

```bash
cf logs cf-summarization-a2a --recent | grep -i error
```

## References

- [Google A2A Protocol Specification](https://google.github.io/A2A/specification/)
- [A2A Python SDK Tutorial](https://google.github.io/A2A/tutorials/python/1-introduction/)
- [A2A Announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [UV Buildpack](https://github.com/yannicklevederpvtl/uv-buildpack)
- [LangChain Documentation](https://python.langchain.com/)

## License

This is a demonstration application for educational purposes.
