# Copilot Bridge for AI Debate Tool

VS Code extension that exposes GitHub Copilot Language Model API via HTTP server.

## Purpose

Enables the AI Debate Tool to automatically invoke Codex (GPT-5.1 Max) without API costs by using your existing GitHub Copilot Pro+ subscription.

## Features

- ✅ HTTP server (default port 8765)
- ✅ Exposes `/invoke-copilot` endpoint
- ✅ Uses VS Code Language Model API
- ✅ Supports GPT-5.1-Codex (Codex 5.1 Max)
- ✅ Auto-starts on VS Code launch
- ✅ Zero API costs (uses your Copilot subscription)

## Requirements

- **VS Code:** 1.104.0 or higher
- **GitHub Copilot Pro+:** Active subscription with access to Codex 5.1 Max
- **GitHub Copilot Extension:** Installed and signed in

## Installation

### Option 1: Local Development

1. Open this directory in VS Code
2. Run `npm install`
3. Press F5 to launch Extension Development Host
4. Bridge server starts automatically on port 8765

### Option 2: Package and Install

```bash
# Install vsce (if not already installed)
npm install -g @vscode/vsce

# Package extension
npm run package

# Install .vsix file
code --install-extension copilot-bridge-0.1.0.vsix
```

## Usage

### Commands

- **Copilot Bridge: Start Server** - Manually start the bridge server
- **Copilot Bridge: Stop Server** - Stop the bridge server
- **Copilot Bridge: Check Status** - Check if server is running

### Configuration

Open VS Code settings (File → Preferences → Settings) and search for "Copilot Bridge":

- **copilotBridge.port** (default: 8765) - HTTP server port
- **copilotBridge.autoStart** (default: true) - Auto-start on VS Code launch
- **copilotBridge.preferredModel** (default: "gpt-5-codex") - Preferred Copilot model
  - `gpt-5-codex` - GPT-5.1-Codex (Codex 5.1 Max)
  - `gpt-5` - GPT-5
  - `claude-opus` - Claude Opus (if available)
  - `auto` - First available model

### API Endpoints

#### POST /invoke-copilot

Invoke Copilot with a prompt.

**Request:**
```json
{
  "prompt": "Your prompt here",
  "model": "gpt-5-codex"  // Optional, uses config default if omitted
}
```

**Response (Success):**
```json
{
  "success": true,
  "response": "Copilot's response",
  "model": "gpt-5.1-codex",
  "vendor": "copilot"
}
```

**Response (Error):**
```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

#### GET /health

Check server health.

**Response:**
```json
{
  "status": "ok",
  "port": 8765
}
```

## Testing

### Manual Test

```bash
# Start bridge (automatic on VS Code launch)

# Test health endpoint
curl http://localhost:8765/health

# Test Copilot invocation
curl -X POST http://localhost:8765/invoke-copilot \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is a state machine?"}'
```

### From Python (AI Debate Tool)

```python
import requests

response = requests.post('http://localhost:8765/invoke-copilot', json={
    'prompt': 'Analyze this code and suggest improvements...',
    'model': 'gpt-5-codex'
})

result = response.json()
print(result['response'])
```

## Troubleshooting

### "Copilot not available"

**Cause:** GitHub Copilot extension not active or not signed in.

**Solution:**
1. Install GitHub Copilot extension from VS Code marketplace
2. Sign in with your GitHub account
3. Verify you have Copilot Pro+ subscription
4. Restart VS Code
5. Restart bridge: Command Palette → "Copilot Bridge: Start Server"

### "No suitable model found"

**Cause:** Preferred model not available in your Copilot subscription.

**Solution:**
1. Open settings: File → Preferences → Settings
2. Search for "Copilot Bridge Preferred Model"
3. Change to "auto" to use any available model
4. Or verify your Copilot Pro+ subscription includes GPT-5.1-Codex

### Port already in use

**Cause:** Another process using port 8765.

**Solution:**
1. Open settings: File → Preferences → Settings
2. Search for "Copilot Bridge Port"
3. Change to different port (e.g., 8766)
4. Restart bridge server
5. Update AI Debate Tool configuration to use new port

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   VS Code Extension                     │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │           HTTP Server (port 8765)             │    │
│  │                                               │    │
│  │  POST /invoke-copilot ──► Language Model API │    │
│  │  GET /health                                  │    │
│  └───────────────────────────────────────────────┘    │
│                        │                               │
│                        ▼                               │
│              VS Code Language Model API                │
│                        │                               │
│                        ▼                               │
│              GitHub Copilot Pro+                       │
│              (GPT-5.1-Codex)                           │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  AI Debate Tool      │
              │  (Python/MCP)        │
              │                      │
              │  CopilotInvoker ──►  │
              │  HTTP Client         │
              └──────────────────────┘
```

## Security

- **Local only:** Server listens on `localhost` only (not accessible from network)
- **No authentication:** Intended for local development use only
- **CORS enabled:** Allows requests from any origin (local tools)

## License

MIT

## Author

AI Debate Tool Team
