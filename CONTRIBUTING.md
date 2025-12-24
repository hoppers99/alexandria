# Contributing to Alexandria

Thank you for your interest in contributing to Bibliotheca Alexandria! This document provides guidelines and instructions for development.

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 22+
- Docker (for PostgreSQL)
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager

### Local Development

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/alexandria.git
   cd alexandria
   ```

2. **Install Python dependencies**

   ```bash
   uv sync
   ```

3. **Install frontend dependencies**

   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env to set ALEXANDRIA_LIBRARY_ROOT
   ```

5. **Start PostgreSQL**

   ```bash
   docker-compose up -d postgres
   ```

6. **Run database migrations**

   ```bash
   uv run alembic upgrade head
   ```

7. **Seed classification data**

   ```bash
   uv run librarian seed
   ```

8. **Start the backend**

   ```bash
   uv run python -m web.main
   ```

9. **Start the frontend** (in a separate terminal)

   ```bash
   cd frontend
   npm run dev
   ```

The web UI will be available at http://localhost:5173, with API at http://localhost:8000.

### Using Docker for Everything

Alternatively, run all services via Docker:

```bash
docker-compose up
```

This starts PostgreSQL, backend (with hot reload), and frontend. The `docker-compose.override.yml` file enables development mode automatically.

## Project Structure

```
alexandria/
├── src/
│   ├── librarian/          # Core cataloguing engine
│   │   ├── enricher/       # External API clients
│   │   ├── inspector/      # File format detection & metadata extraction
│   │   ├── classifier.py   # DDC classification logic
│   │   ├── filer.py        # File organisation
│   │   ├── covers.py       # Cover extraction & processing
│   │   ├── config.py       # Application settings
│   │   └── db/             # Database models & session
│   └── web/                # FastAPI web application
│       ├── api/            # API route handlers
│       ├── config.py       # Web-specific settings
│       └── main.py         # Application entry point
├── frontend/               # SvelteKit application
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.ts      # API client
│   │   │   └── components/ # Reusable UI components
│   │   └── routes/         # Page components
│   └── vite.config.ts
├── alembic/                # Database migrations
├── docs/                   # Documentation
└── tests/                  # Test suite
```

## Code Style

### Python

- Follow PEP 8
- Use type hints for all function signatures
- Format with `ruff format`
- Lint with `ruff check`

```bash
uv run ruff format src/
uv run ruff check src/
```

### Frontend (Svelte/TypeScript)

- Use Svelte 5 runes (`$state()`, `$derived()`, `$effect()`) - NOT Svelte 4 stores
- Use TypeScript for all new code
- Format with Prettier (via `npm run format`)

```bash
cd frontend
npm run check    # Type check
npm run format   # Format code
```

### Spelling

Use **New Zealand English** spelling (e.g., "colour" not "color", "organised" not "organized").

## Database Migrations

When modifying database models:

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "Description of change"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

## API Development

The backend uses FastAPI with automatic OpenAPI documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

When adding new endpoints:
1. Add the route handler in `src/web/api/`
2. Add corresponding TypeScript types and functions in `frontend/src/lib/api.ts`
3. Update tests as needed

## Frontend Components

Reusable components live in `frontend/src/lib/components/`:

| Component | Purpose |
|-----------|---------|
| `BookCard.svelte` | Book cover card with metadata overlay |
| `Lightbox.svelte` | Image zoom modal |
| `MetadataForm.svelte` | Editable metadata form with autocomplete |
| `SearchPanel.svelte` | ISBN/title search interface |
| `SearchCandidateCard.svelte` | Display search result with "Use" button |
| `SearchResultCard.svelte` | Single result with Merge/Replace actions |

When creating new components, export them from `frontend/src/lib/components/index.ts`.

## Commit Messages

Use clear, descriptive commit messages:

```
Add cover replacement from search results

- Add POST /api/items/{id}/cover endpoint
- Add "Use Cover" button to SearchCandidateCard
- Download and save cover to item folder
```

## Pull Requests

1. Create a feature branch from `main`
2. Make your changes with clear commits
3. Ensure tests pass and code is formatted
4. Submit a PR with a clear description of changes

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues and documentation first
- Include relevant error messages and steps to reproduce
