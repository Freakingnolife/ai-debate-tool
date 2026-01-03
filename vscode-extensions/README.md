# VS Code Extensions for AI Debate Tool

This directory contains VS Code extensions that enable automatic AI invocation for the AI Debate Tool.

## Extensions

### 1. Copilot Bridge (`copilot-bridge/`)

Exposes the GitHub Copilot Language Model API to the AI Debate Tool for automatic AI invocation.

**Requirements:**
- VS Code 1.104.0+
- GitHub Copilot subscription

**Installation:**
```bash
cd copilot-bridge
npm install
npm run compile
npm run package  # Creates .vsix file
```

Then install the `.vsix` file in VS Code: Extensions → ... → Install from VSIX

### 2. Codex Bridge (`codex-bridge/`)

Bridges the OpenAI ChatGPT/Codex extension for AI debates.

**Requirements:**
- VS Code 1.104.0+
- OpenAI ChatGPT extension (`openai.chatgpt`)

**Installation:**
```bash
cd codex-bridge
npm install
npm run compile
npm run package  # Creates .vsix file
```

## Features

Both extensions:
- Start HTTP server on port 8765 (configurable)
- Auto-start on VS Code startup
- Commands for start/stop/status
- Health check endpoint

## HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/invoke-copilot` | POST | Invoke Copilot (copilot-bridge) |
| `/invoke-codex` | POST | Invoke Codex (codex-bridge) |

## Usage with AI Debate Tool

1. Install one of the bridge extensions
2. Start VS Code
3. The bridge server starts automatically
4. Configure the AI Debate Tool to use the bridge:

```python
from ai_debate_tool.services.copilot_invoker import CopilotInvoker

copilot = CopilotInvoker()
status = copilot.get_status()
print(f"Bridge available: {status['available']}")
```

## Configuration

### Copilot Bridge Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `copilotBridge.port` | 8765 | HTTP server port |
| `copilotBridge.autoStart` | true | Auto-start on VS Code startup |
| `copilotBridge.preferredModel` | gpt-5-codex | Preferred model |

### Codex Bridge Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `codexBridge.port` | 8765 | HTTP server port |
| `codexBridge.autoStart` | true | Auto-start on VS Code startup |
| `codexBridge.integrationMode` | auto | Integration mode (auto/command/api/clipboard) |

## Troubleshooting

### Bridge not responding

1. Check if VS Code is running
2. Run command: "Copilot Bridge: Check Status"
3. Verify port 8765 is not in use

### Copilot not available

1. Ensure GitHub Copilot subscription is active
2. Sign in to GitHub in VS Code
3. Restart VS Code

### Codex extension not found

1. Install OpenAI ChatGPT extension from marketplace
2. Restart VS Code
