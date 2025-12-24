# Technology Stack

## Overview

All components are chosen for:
- Open source licensing compatible with GPL v3
- Active maintenance and community support
- Docker-friendly deployment
- Suitability for self-hosted environments

## Core Stack

| Layer | Technology | Licence | Purpose |
|-------|------------|---------|---------|
| **Backend** | Python 3.11+ | PSF | Runtime |
| **API Framework** | FastAPI | MIT | REST API, async support |
| **Database** | PostgreSQL 17 | PostgreSQL (BSD-like) | Metadata, search, users |
| **Cache/Queue** | Redis | BSD-3-Clause | Caching, job queue backend |
| **Task Queue** | ARQ or Celery | MIT / BSD | Background job processing |
| **ORM** | SQLAlchemy 2.0 | MIT | Database abstraction |
| **Migrations** | Alembic | MIT | Schema versioning |

## Frontend Stack

| Component | Technology | Licence | Purpose |
|-----------|------------|---------|---------|
| **Framework** | Vue.js 3 or Svelte | MIT | Reactive UI |
| **CSS** | Tailwind CSS | MIT | Styling |
| **EPUB Reader** | epub.js | BSD-2-Clause | In-browser e-book reading |
| **PDF Viewer** | PDF.js | Apache 2.0 | In-browser PDF viewing |
| **Video Player** | Video.js | Apache 2.0 | Video streaming |
| **Audio Player** | Howler.js | MIT | Audio playback |
| **Icons** | Lucide | ISC | Icon set |

## Metadata Extraction Tools

| Format | Tool | Licence | Notes |
|--------|------|---------|-------|
| **E-books** | ebook-meta (Calibre) | GPL v3 | Called as external process |
| **E-books** | ebooklib | AGPL v3 | Pure Python EPUB library |
| **PDF** | pdftotext (Poppler) | GPL v2+ | Text extraction |
| **PDF** | pypdf | BSD | Pure Python, basic extraction |
| **Audio/Video** | ffprobe (FFmpeg) | LGPL/GPL | Called as external process |
| **Images** | Pillow | HPND | Cover processing |

### Note on GPL Tools

Calibre CLI tools (ebook-meta, ebook-convert) and ffprobe are called as **external processes**, not linked as libraries. This is standard practice and does not require the calling application to be GPL-licensed. However, since Alexandria is GPL v3 anyway, this is a non-issue.

## External APIs (Optional Enrichment)

| API | Purpose | Terms |
|-----|---------|-------|
| **Open Library** | Book metadata, covers | CC0 data, free API |
| **Google Books** | Book metadata | Free tier available |
| **MusicBrainz** | Audio metadata | CC0 data, free API |
| **TMDB** | Video/film metadata | Free API with attribution |
| **Audible** | Audiobook metadata | Unofficial/scraping |
| **ISBN DB** | ISBN lookup | Paid tiers available |

## Optional Components

| Component | Technology | Licence | Purpose |
|-----------|------------|---------|---------|
| **Full-text search** | Meilisearch | MIT | Advanced search (alternative to pg_trgm) |
| **TTS** | Piper | MIT | Text-to-speech for e-books |
| **TTS** | Coqui TTS | MPL 2.0 | Alternative TTS engine |
| **Reverse Proxy** | Traefik / Nginx | MIT / BSD | Production deployment |
| **Auth** | Authelia | Apache 2.0 | SSO integration (optional) |

## Deployment

### Docker Images

```yaml
# docker-compose.yml structure
services:
  alexandria:
    build: .
    # Python + FastAPI + frontend assets

  postgres:
    image: postgres:17-alpine

  redis:
    image: redis:7-alpine
```

### Supported Platforms

- **Unraid** - Community Applications template
- **TrueNAS Scale** - Helm chart or custom app
- **Proxmox** - LXC or VM with Docker
- **Synology** - Docker package
- **Generic Linux** - Docker Compose
- **Kubernetes** - Helm chart (future)

## Development Tools

| Tool | Purpose |
|------|---------|
| **uv** or **poetry** | Python dependency management |
| **pytest** | Testing |
| **ruff** | Linting and formatting |
| **mypy** | Type checking |
| **pre-commit** | Git hooks |
| **Docker Compose** | Local development environment |

## Browser Support

Target modern browsers with ES2020+ support:
- Chrome/Edge 88+
- Firefox 78+
- Safari 14+

No IE11 support planned.
