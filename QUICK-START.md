# Quick Start Guide - A2A Summarization Agent

## Deploy in 3 Steps

### 1. Deploy to Cloud Foundry

```bash
cd cf-jupyterlab-to-a2a
cf push
```

### 2. Get Your App URL

```bash
APP_URL=$(cf app cf-summarization-a2a | grep "urls:" | awk '{print $2}')
echo "Your app is at: https://${APP_URL}"
```

### 3. Test the Agent

#### View Agent Card
```bash
curl -s "https://${APP_URL}/.well-known/agent.json" | jq
```

#### Trigger Summarization
```bash
curl --location "https://${APP_URL}/" \
  --header 'Content-Type: application/json' \
  --data '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/stream",
    "params": {
      "message": {
        "role": "user",
        "parts": [{
          "kind": "text",
          "text": "Cloud Foundry is an open-source platform-as-a-service that simplifies application deployment and scaling."
        }],
        "messageId": "test-123"
      }
    }
  }'
```

## Expected Output

The agent will return a JSON-RPC response with:
- **Task ID**: Unique identifier for the request
- **Status Updates**: "submitted" → "working" → "completed"
- **Summary**: The summarized text in the final message

## Troubleshooting

```bash
# Check app status
cf apps

# View logs
cf logs cf-summarization-a2a --recent

# Check service bindings
cf services
```

For more details, see [README.md](README.md)
