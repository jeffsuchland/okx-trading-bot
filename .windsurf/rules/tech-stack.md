---
trigger: always_on
---

<tech_stack>

## Technology Stack

### Core

- **Language:** Python 3.11+
- **Backend Framework:** FastAPI (REST API for dashboard ↔ bot communication)
- **Frontend Framework:** React 18 + Tailwind CSS + Vite
- **Package Manager (Python):** pip / requirements.txt
- **Package Manager (JS):** npm
- **Exchange SDK:** python-okx (official OKX V5 SDK) + WebSocket via websockets library

### Testing

- **Test Framework:** pytest
- **Coverage Tool:** pytest-cov
- **Frontend Testing:** Vitest + React Testing Library

### Development Tools

- **Linter:** ruff (Python), ESLint (JS/React)
- **Formatter:** ruff format (Python), Prettier (JS/React)
- **Environment:** python-dotenv for .env management

</tech_stack>

<coding_conventions>

## Coding Conventions

### Code Style

- Follow PEP 8 guidelines (Python)
- Use snake_case for Python variables/functions, camelCase for JS/React
- Maximum line length: 120 characters
- Type hints required on all Python function signatures

### Testing Standards

- Minimum test coverage: 80%
- Test file naming: `test_<module>.py` (Python), `*.test.tsx` (React)
- All features must have unit tests before marking as complete
- Mock all external API calls in tests

### Git Workflow

- Commit message format: `<type>: <description>`
- Types: feat, fix, docs, test, refactor, chore
- All commits must pass tests

### Security

- API keys via .env only, never hardcoded
- .env in .gitignore
- Secrets loaded through python-dotenv

## Verification Commands

```bash
# Run Python tests
pytest --cov=src tests/ -v

# Run frontend tests
npm test

# Check Python code style
ruff check src/

# Check frontend code style
npx eslint src/

# Build frontend
npm run build
```

</coding_conventions>
