# Contributing to IPTV Web

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.10+
- pip
- ffmpeg (for transcoding)

### Local Development

```bash
# Clone the repository
git clone https://github.com/thunderbird-esq/mermaid-lane.git
cd mermaid-lane/web

# Set up backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000
```

### Running Tests

```bash
cd backend

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term
```

## Project Structure

```
web/
├── backend/           # FastAPI Python backend
│   ├── app/
│   │   ├── config.py  # Configuration
│   │   ├── main.py    # Application entry
│   │   ├── models/    # Pydantic models
│   │   ├── routers/   # API endpoints
│   │   └── services/  # Business logic
│   └── tests/         # Test suite
├── frontend/          # Static frontend
│   ├── css/           # Stylesheets
│   └── js/            # JavaScript modules
└── docker-compose.yml
```

## Coding Standards

### Python

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write docstrings for public functions
- Keep functions focused and under 50 lines

### JavaScript

- Use modern ES6+ syntax
- Add JSDoc comments for functions
- Follow existing code style

### Commits

- Use [Conventional Commits](https://conventionalcommits.org/) format:
  - `feat:` New features
  - `fix:` Bug fixes
  - `test:` Adding tests
  - `docs:` Documentation
  - `refactor:` Code refactoring
  - `chore:` Maintenance tasks

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Run tests (`python -m pytest tests/`)
5. Commit with conventional commit message
6. Push to your fork
7. Open a Pull Request

## Areas for Contribution

### High Priority

- [ ] Add more test coverage (currently 39%)
- [ ] Implement geo-bypass Level 2 (proxy scavenging)
- [ ] Add stream fallback logic
- [ ] Improve EPG data fetching

### Good First Issues

- Add JSDoc comments to frontend JavaScript
- Add type hints to backend Python code
- Improve error messages
- Add more unit tests

## Questions?

Open an issue or discussion on GitHub.
