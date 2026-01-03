# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-01-03

### Added
- **VS Code Extensions**: Full automation for AI debates
  - `copilot-bridge/` - GitHub Copilot integration for VS Code
  - `codex-bridge/` - OpenAI Codex/ChatGPT integration for VS Code
  - HTTP bridge server on port 8765 (configurable)
  - Auto-start on VS Code startup
  - Commands for start/stop/status

### VS Code Extension Features
- **Copilot Bridge**:
  - Uses VS Code's built-in Language Model API
  - Supports multiple models (GPT-5-Codex, GPT-5, Claude Opus)
  - No external dependencies

- **Codex Bridge**:
  - Multiple integration modes (command, API, clipboard)
  - Auto-detection of best integration method
  - Requires OpenAI ChatGPT extension

### Installation
```bash
# Copilot Bridge
cd vscode-extensions/copilot-bridge
npm install && npm run compile && npm run package

# Codex Bridge
cd vscode-extensions/codex-bridge
npm install && npm run compile && npm run package
```

---

## [1.1.0] - 2025-01-03

### Added
- **MCP Server Integration**: Full MCP server for Claude Desktop
  - `ai-debate server` command to start MCP server
  - 10 MCP tools for debate orchestration
  - Stdio-based protocol for Claude integration
  - Codex CLI bridge for automated invocation
- New CLI command: `ai-debate server`
- MCP configuration file: `mcp_config.json`

### MCP Tools
- `debate_check_complexity` - Check if change requires debate
- `debate_start_session` - Start new debate session
- `debate_submit_proposal` - Submit AI proposal
- `debate_check_consensus` - Check consensus status
- `debate_override` - User override
- `debate_get_decision_pack` - Get decision pack
- `debate_start_auto` - One-command automation
- `debate_submit_codex_response` - Submit Codex response
- `debate_check_copilot_status` - Check Copilot bridge
- `debate_configure_copilot` - Configure Copilot bridge

### Configuration
Add to Claude Desktop settings (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "ai-debate-tool": {
      "command": "ai-debate",
      "args": ["server"]
    }
  }
}
```

---

## [1.0.0] - 2025-01-03

### Added
- Initial release of AI Debate Tool as standalone package
- CLI tool with commands: `run`, `check`, `history`, `config`
- ParallelDebateOrchestrator for dual-AI debates
- Consensus scoring (0-100) with interpretations
- Pattern detection and learning from debate history
- Risk prediction based on historical patterns
- Debate caching with 5-minute TTL
- File-based session management
- Comprehensive documentation
- Example scripts

### Features
- **Dual-AI Debates**: Get perspectives from Claude and Codex
- **Fast Execution**: 10-18 seconds per debate
- **Zero API Costs**: Uses Codex CLI (no ongoing fees)
- **Intelligence System**: Pattern detection, risk prediction, learning
- **Caching**: Repeated requests are served from cache

---

## Roadmap

- v1.0.0: Core library + CLI
- v1.1.0: MCP server integration
- v1.2.0 (Current): VS Code extensions

---

## [Unreleased]

### Planned
- Web UI for debate visualization
- Custom LLM provider support
