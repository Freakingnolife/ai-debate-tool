# Contributing to AI Debate Tool

Thank you for your interest in contributing to AI Debate Tool!

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ai-debate-tool/ai-debate-tool.git
   cd ai-debate-tool
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode:**
   ```bash
   pip install -e .[dev]
   ```

4. **Run tests:**
   ```bash
   pytest --cov
   ```

5. **Format code:**
   ```bash
   black src/
   ```

## Code Style

- Use [Black](https://black.readthedocs.io/) for formatting (line length: 100)
- Follow PEP 8 guidelines
- Add type hints where practical
- Write docstrings for public functions

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for good coverage on new code

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/ai_debate_tool --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and formatting
5. Commit with clear message (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Commit Messages

Use clear, descriptive commit messages:

```
feat: Add new consensus algorithm
fix: Handle edge case in debate cache
docs: Update CLI reference
test: Add tests for pattern detector
refactor: Simplify orchestrator logic
```

## Reporting Issues

When reporting issues, please include:

- Python version
- OS and version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/traceback if applicable

## Questions?

Open an issue or start a discussion on GitHub.

Thank you for contributing!
