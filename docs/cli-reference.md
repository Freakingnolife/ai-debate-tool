# CLI Reference

Complete reference for the `ai-debate` command-line interface.

## Global Options

```bash
ai-debate --version  # Show version
ai-debate --help     # Show help
```

---

## Commands

### `ai-debate run`

Run a debate on a topic/file.

```bash
ai-debate run <topic> --file <path> [options]
```

**Arguments:**
- `topic` - The topic or question to debate

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--file PATH` | `-f` | Path to file to debate (required) |
| `--focus TEXT` | `-F` | Focus areas (can be repeated) |
| `--target INT` | `-t` | Target consensus score (default: 75) |
| `--output PATH` | `-o` | Save results to JSON file |
| `--verbose` | `-v` | Verbose output |

**Examples:**
```bash
# Basic debate
ai-debate run "Review this design" --file design.md

# With multiple focus areas
ai-debate run "Security review" --file auth.py -F security -F validation -F testing

# Save results and show verbose output
ai-debate run "Architecture review" --file arch.md -o results.json -v

# Set target consensus
ai-debate run "Critical change review" --file critical.py -t 90
```

**Exit Codes:**
- `0` - Consensus meets or exceeds target
- `1` - Consensus below target or error

---

### `ai-debate check`

Check if a change requires debate (complexity scoring).

```bash
ai-debate check <request> [options]
```

**Arguments:**
- `request` - Description of the proposed change

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--files TEXT` | `-f` | Files involved (can be repeated) |
| `--threshold INT` | `-t` | Complexity threshold (default: 40) |
| `--json` | | Output as JSON |

**Examples:**
```bash
# Check a change
ai-debate check "Add user authentication" --files auth.py models.py

# With custom threshold
ai-debate check "Update config" --threshold 20

# JSON output for scripting
ai-debate check "Major refactor" --files *.py --json
```

**Exit Codes:**
- `0` - Debate NOT required (simple change)
- `1` - Debate recommended (complex change)

---

### `ai-debate history`

View debate history.

```bash
ai-debate history [options]
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--limit INT` | `-n` | Number of entries (default: 10) |
| `--stats` | | Show statistics only |
| `--json` | | Output as JSON |

**Examples:**
```bash
# View last 5 debates
ai-debate history --limit 5

# View statistics
ai-debate history --stats

# JSON output
ai-debate history --json
```

---

### `ai-debate config`

Manage configuration.

```bash
ai-debate config [options]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--init` | Initialize configuration file |
| `--show` | Show current configuration |
| `--path` | Show config file path |

**Examples:**
```bash
# Initialize config
ai-debate config --init

# Show current config
ai-debate config --show

# Get config path
ai-debate config --path
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_AI_DEBATE` | Enable/disable debates | `true` |
| `DEBATE_COMPLEXITY_THRESHOLD` | Complexity threshold | `40` |
| `DEBATE_TARGET_CONSENSUS` | Target consensus | `75` |
| `DEBATE_MAX_ROUNDS` | Maximum debate rounds | `5` |

---

## Configuration File

Location: `~/.config/ai-debate-tool/config.json`

```json
{
    "enabled": true,
    "complexity_threshold": 40,
    "target_consensus": 75,
    "max_rounds": 5,
    "enable_cache": true,
    "enable_intelligence": true,
    "log_level": "INFO"
}
```

---

## Scripting Examples

### CI/CD Integration

```bash
#!/bin/bash
# Run debate and fail if consensus too low
ai-debate run "Review PR changes" --file changes.md -t 80
if [ $? -ne 0 ]; then
    echo "Debate consensus below threshold"
    exit 1
fi
```

### Pre-commit Hook

```bash
#!/bin/bash
# Check if changes need debate
ai-debate check "$(git log -1 --pretty=%B)" --files $(git diff --name-only HEAD~1)
if [ $? -eq 1 ]; then
    echo "Consider running a debate before committing"
fi
```
