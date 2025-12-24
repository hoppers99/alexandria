# Web UI Design Document

## Overview

The Alexandria web interface provides patron access to the digital library. It follows an **API-first design**, with a clean, book-focused UI inspired by calibre-web's simplicity and modern self-hosted apps like Immich and Audiobookshelf.

## Design Principles

1. **Books are the hero** - Covers prominently displayed, minimal chrome
2. **Mobile-first** - Primary use case is browsing/reading on phone or tablet
3. **API-first** - All functionality exposed via REST API, enabling third-party clients
4. **Progressive enhancement** - Works without JavaScript, enhanced with it
5. **Accessibility** - WCAG AA compliance, keyboard navigation, screen reader support

## Technology Stack

### Backend
| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | FastAPI | Already used for Librarian, async, OpenAPI docs |
| Auth | Session-based + Forward Auth | Local auth first, Authelia/OIDC later |
| Database | PostgreSQL | Already in place |
| Cache | Redis | Session storage, API caching |
| Task Queue | ARQ | Background jobs (cover generation, etc.) |

### Frontend
| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | SvelteKit | Fast, lightweight, great DX, SSR support |
| Styling | Tailwind CSS | Utility-first, easy dark mode |
| EPUB Reader | Foliate-js | Modern, same engine as Readest |
| Icons | Lucide | Consistent, MIT licensed |
| Charts | Chart.js | Reading statistics |

**Why SvelteKit over Vue/React?**
- Smaller bundle size (critical for mobile)
- Built-in SSR for fast initial load
- Simpler mental model
- TypeScript support
- Growing ecosystem with good component libraries

### Alternative: HTMX + Jinja2
For a simpler approach, we could use server-rendered HTML with HTMX for interactivity:
- Simpler deployment (no separate frontend build)
- Works without JavaScript
- Fewer dependencies
- Trade-off: Less sophisticated reader experience

## Authentication Architecture

### Phase 1: Local Authentication
- Username/password stored in PostgreSQL
- Argon2id password hashing
- Session cookies (httpOnly, secure, sameSite)
- CSRF protection
- Rate limiting on login

### Phase 2: Forward Auth (Authelia)
Support trusted header authentication for reverse proxy setups:

```
# Traefik / nginx passes these headers after Authelia auth
X-Forwarded-User: username
X-Forwarded-Email: user@example.com
X-Forwarded-Groups: users,admins
```

Configuration:
```yaml
auth:
  mode: local | forward_auth | both
  forward_auth:
    user_header: X-Forwarded-User
    email_header: X-Forwarded-Email
    groups_header: X-Forwarded-Groups
    admin_group: admins
    auto_create_users: true
```

### Phase 3: OIDC (Optional)
Direct OAuth2/OIDC integration for environments without a proxy:
- Support for Authelia, Authentik, Keycloak, Zitadel
- Standard OIDC discovery
- Group/role mapping

## User Roles & Permissions

| Role | Permissions |
|------|-------------|
| Guest | Browse, search (if enabled) |
| User | Browse, search, download, read, personal piles, ratings |
| Admin | All user permissions + metadata editing, user management, settings |

### Terminology

| Term | Meaning |
|------|---------|
| **Library** | The whole Alexandria instance - all content |
| **Collection** | Admin-defined grouping with access control (e.g., Comics, Kids, Restricted Section) |
| **Pile** | Personal user lists (To Read, Reading, Finished, custom) |

### Collections
- Admin-created groupings of content within the library
- Users can be granted access to specific collections
- Like the "Restricted Section" at a real library
- Age ratings can also filter content visibility

```python
class Collection:
    id: int
    name: str
    description: str | None
    age_rating: str | None  # G, PG, M, R18, etc.

class UserCollectionAccess:
    user_id: int
    collection_id: int
    # If no access record, user cannot see the collection
```

## Core Views

### Home Dashboard
```
┌─────────────────────────────────────────────────┐
│  [Logo]  Alexandria         [Search] [User ▼]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  Continue Reading                               │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐               │
│  │cover│ │cover│ │cover│ │cover│  ───►         │
│  │ 45% │ │ 12% │ │ 78% │ │ 3%  │               │
│  └─────┘ └─────┘ └─────┘ └─────┘               │
│                                                 │
│  Recently Added                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐               │
│  │cover│ │cover│ │cover│ │cover│  ───►         │
│  │     │ │     │ │     │ │     │               │
│  └─────┘ └─────┘ └─────┘ └─────┘               │
│                                                 │
│  Browse by Author    Browse by Series           │
│  Browse by Genre     Browse by DDC              │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Browse View (Grid/List)
```
┌─────────────────────────────────────────────────┐
│  ← Authors                    [Grid│List] [▼]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  Brandon Sanderson (42 books)                   │
│                                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐       │
│  │     │ │     │ │     │ │     │ │     │       │
│  │cover│ │cover│ │cover│ │cover│ │cover│       │
│  │     │ │     │ │     │ │     │ │     │       │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘       │
│  Elantris  Mistborn  Mistborn  Mistborn  ...   │
│            #1        #2        #3              │
│                                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐       │
│  │     │ │     │ │     │ │     │ │     │       │
│  ...                                            │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Book Detail
```
┌─────────────────────────────────────────────────┐
│  ← Back                              [Edit ✎]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌───────────┐  Mistborn: The Final Empire     │
│  │           │  by Brandon Sanderson            │
│  │   cover   │                                  │
│  │           │  ★★★★☆  (your rating)           │
│  │           │                                  │
│  └───────────┘  Series: Mistborn Era 1 (#1)    │
│                 Published: 2006 • Tor Books     │
│                                                 │
│  [Read] [Download ▼] [Add to Pile ▼]           │
│                                                 │
│  ─────────────────────────────────────────────  │
│                                                 │
│  In a world where ash falls from the sky and   │
│  mists dominate the night, a young street      │
│  urchin named Vin discovers she has the...     │
│  [Show more]                                    │
│                                                 │
│  ─────────────────────────────────────────────  │
│                                                 │
│  Genres: Fantasy, Epic Fantasy, Magic          │
│  DDC: 813.6 (American fiction)                 │
│  ISBN: 978-0765311788                          │
│                                                 │
│  ─────────────────────────────────────────────  │
│                                                 │
│  More in this series                            │
│  ┌─────┐ ┌─────┐ ┌─────┐                       │
│  │ #1  │ │ #2  │ │ #3  │                       │
│  │ ██  │ │     │ │     │                       │
│  └─────┘ └─────┘ └─────┘                       │
│                                                 │
│  Available formats: EPUB • MOBI • PDF          │
│                                                 │
└─────────────────────────────────────────────────┘
```

### In-Browser Reader
```
┌─────────────────────────────────────────────────┐
│  ☰  Mistborn: The Final Empire           ✕    │
├─────────────────────────────────────────────────┤
│                                                 │
│     In a world where ash falls from the sky    │
│  and mists dominate the night, an evil         │
│  immortal emperor has ruled for a thousand     │
│  years.                                         │
│                                                 │
│     Vin, a street urchin, discovers she has    │
│  powers she never knew existed—powers that     │
│  could be the key to defeating the Lord        │
│  Ruler and freeing her people.                 │
│                                                 │
│     But first, she must learn to trust the     │
│  man who would teach her to use them: a        │
│  man who has survived the Lord Ruler's         │
│  deepest dungeon, and who leads the            │
│  rebellion against him.                        │
│                                                 │
│                   ◄  12%  ►                    │
│                                                 │
└─────────────────────────────────────────────────┘

Reader sidebar (☰):
- Table of Contents
- Bookmarks
- Search in book
- Settings (font, size, theme, margins)
- Reading statistics
```

### Mobile Navigation
```
┌─────────────────────────────────────────────────┐
│  Alexandria                      [🔍] [👤]     │
├─────────────────────────────────────────────────┤
│                                                 │
│  [Content area - scrollable]                   │
│                                                 │
│                                                 │
├─────────────────────────────────────────────────┤
│   🏠      📚      🔍      📖      ☰           │
│  Home   Library  Search  Reading  More         │
└─────────────────────────────────────────────────┘
```

## User Features

### Piles
Built-in piles (cannot be deleted):
- **To Read Pile** - Books queued for reading
- **Reading Pile** - In progress (auto-populated from reader)
- **Finished Pile** - Completed books

User-created piles:
- Custom name
- Optional description
- Privacy setting (private/public)
- Sort order preference

### Reading Progress
- Tracked per-user, per-book
- Stored as percentage (0.0-100.0) and location string (for EPUB CFI)
- Synced from:
  - Built-in web reader
  - KOReader sync API
  - Manual update via API
- Displayed on book cards and detail pages

### Reading Statistics
- Books read this month/year/all-time
- Pages/hours read
- Reading streak
- Favourite authors/genres
- Reading goals (optional)

### Age Ratings
Content can be tagged with age ratings:
- **G** - General audiences
- **PG** - Parental guidance suggested
- **M** - Mature audiences
- **R18** - Restricted

Users have a maximum viewable rating in their profile. Content above their rating is hidden from browse/search.

## Admin Features

### Dashboard
- Library statistics (total books, formats, storage used)
- Recent activity
- Processing queue status
- System health

### User Management
- Create/edit/delete users
- Assign library access
- Set roles and age ratings
- View reading activity

### Metadata Editing
- Edit title, authors, description
- Manage series membership
- Edit tags/genres
- Change DDC classification
- Upload/change cover

### Review Queue
Integration with Librarian's review queue:
- View pending items
- Search by ISBN or title
- File with corrected metadata
- Mark as duplicate/skip

## API Design

Alexandria uses a **hybrid API architecture**:

- **GraphQL** (`/graphql`) - For catalogue queries where clients need flexibility in selecting fields and related data (books, authors, series, piles, progress)
- **REST** (`/api/*`) - For simple operations, file serving, authentication, and admin actions

### Why Hybrid?

| Use Case | Best Fit | Reason |
|----------|----------|--------|
| Browse library | GraphQL | Need books + authors + covers in one request |
| Book detail | GraphQL | Need book + files + series + related in one query |
| Search | GraphQL | Flexible field selection, faceted results |
| Download file | REST | Simple binary response, HTTP caching |
| Cover images | REST | Cacheable, CDN-friendly |
| Authentication | REST | Simple request/response, standard patterns |
| Admin actions | REST | CRUD operations, clear HTTP semantics |
| OPDS catalog | REST | Standard protocol, XML format |
| KOReader sync | REST | Must match existing protocol spec |

### GraphQL Schema

```graphql
type Query {
  # Catalogue browsing
  items(
    page: Int = 1
    perPage: Int = 24
    sort: ItemSort = DATE_ADDED
    order: SortOrder = DESC
    search: String
    authorId: Int
    series: String
    tag: String
    mediaType: String
    format: String
  ): ItemConnection!

  item(id: Int!): Item

  authors(
    page: Int = 1
    perPage: Int = 50
    search: String
    sort: AuthorSort = NAME
  ): AuthorConnection!

  author(id: Int!): Author

  series(
    page: Int = 1
    perPage: Int = 50
    search: String
  ): SeriesConnection!

  seriesByName(name: String!): Series

  # User data
  me: User
  myPiles: [Pile!]!
  myProgress(itemId: Int): [Progress!]!
  myStats: ReadingStats!

  # System
  libraryStats: LibraryStats!
}

type Item {
  id: Int!
  uuid: String!
  title: String!
  subtitle: String
  sortTitle: String
  description: String
  publisher: String
  publishDate: String
  language: String!
  isbn: String
  isbn13: String
  seriesName: String
  seriesIndex: Float
  tags: [String!]
  mediaType: String!
  classificationCode: String
  pageCount: Int
  coverUrl: String
  dateAdded: String!

  # Relations
  creators: [ItemCreator!]!
  files: [File!]!
  classification: Classification
  seriesItems: [Item!]  # Other items in same series

  # User-specific (requires auth)
  progress: Progress
  inPiles: [Pile!]
}

type ItemCreator {
  creator: Creator!
  role: String!
  position: Int!
}

type Creator {
  id: Int!
  name: String!
  sortName: String
  bio: String
  photoUrl: String

  # Relations
  items(role: String = "author"): [Item!]!
  itemCount: Int!
}

type File {
  id: Int!
  format: String!
  sizeBytes: Int
  downloadUrl: String!
}

type Series {
  name: String!
  items: [Item!]!
  authors: [String!]!
  coverUrl: String
}

type Pile {
  id: Int!
  name: String!
  description: String
  isBuiltIn: Boolean!
  itemCount: Int!
  items: [PileItem!]!
}

type PileItem {
  item: Item!
  addedAt: String!
  notes: String
}

type Progress {
  item: Item!
  percent: Float
  position: String
  lastAccessed: String!
  completed: Boolean!
  completedAt: String
}

type ReadingStats {
  totalRead: Int!
  readThisYear: Int!
  readThisMonth: Int!
  currentStreak: Int!
  favouriteAuthors: [AuthorStat!]!
  favouriteTags: [TagStat!]!
}

type LibraryStats {
  totalItems: Int!
  totalFiles: Int!
  totalAuthors: Int!
  totalSeries: Int!
  totalSizeBytes: Int!
  formats: [FormatCount!]!
  mediaTypes: [MediaTypeCount!]!
}

# Connections for pagination
type ItemConnection {
  items: [Item!]!
  total: Int!
  page: Int!
  perPage: Int!
  pages: Int!
}

type AuthorConnection {
  authors: [Creator!]!
  total: Int!
  page: Int!
  perPage: Int!
  pages: Int!
}

type SeriesConnection {
  series: [Series!]!
  total: Int!
  page: Int!
  perPage: Int!
  pages: Int!
}

# Mutations
type Mutation {
  # Piles
  createPile(name: String!, description: String): Pile!
  updatePile(id: Int!, name: String, description: String): Pile!
  deletePile(id: Int!): Boolean!
  addToPile(pileId: Int!, itemId: Int!, notes: String): PileItem!
  removeFromPile(pileId: Int!, itemId: Int!): Boolean!

  # Progress
  updateProgress(
    itemId: Int!
    percent: Float
    position: String
    completed: Boolean
  ): Progress!
}

enum ItemSort {
  TITLE
  DATE_ADDED
  SERIES_NAME
  AUTHOR
}

enum AuthorSort {
  NAME
  BOOK_COUNT
}

enum SortOrder {
  ASC
  DESC
}
```

### Example GraphQL Queries

**Home page (continue reading + recent):**
```graphql
query HomePage {
  myProgress(limit: 6) {
    item {
      id
      title
      coverUrl
      seriesName
      seriesIndex
      creators { creator { name } role }
    }
    percent
    lastAccessed
  }

  items(perPage: 12, sort: DATE_ADDED) {
    items {
      id
      title
      coverUrl
      creators { creator { name } role }
    }
  }
}
```

**Book detail page:**
```graphql
query BookDetail($id: Int!) {
  item(id: $id) {
    id
    title
    subtitle
    description
    publisher
    publishDate
    isbn13
    seriesName
    seriesIndex
    tags
    coverUrl

    creators {
      creator { id name }
      role
    }

    files {
      id
      format
      sizeBytes
      downloadUrl
    }

    seriesItems {
      id
      title
      seriesIndex
      coverUrl
    }

    progress {
      percent
      lastAccessed
    }

    inPiles {
      id
      name
    }
  }
}
```

**Author browse:**
```graphql
query AuthorBooks($authorId: Int!) {
  author(id: $authorId) {
    name
    bio
    photoUrl
    itemCount

    items {
      id
      title
      seriesName
      seriesIndex
      coverUrl
      publishDate
    }
  }
}
```

### REST Endpoints

REST remains for operations where it's the better fit:

```
# Authentication
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me
POST   /api/auth/refresh

# Library Items
GET    /api/items                    # List/search items
GET    /api/items/{id}               # Item details
GET    /api/items/{id}/cover         # Cover image
GET    /api/items/{id}/files         # Available files
GET    /api/files/{id}/download      # Download file

# Browse
GET    /api/authors                  # List authors
GET    /api/authors/{id}             # Author with books
GET    /api/series                   # List series
GET    /api/series/{id}              # Series with books
GET    /api/genres                   # List genres/tags

# User Data
GET    /api/me/piles                 # User's piles
POST   /api/me/piles                 # Create pile
PUT    /api/me/piles/{id}            # Update pile
DELETE /api/me/piles/{id}            # Delete pile
POST   /api/me/piles/{id}/items      # Add item to pile
DELETE /api/me/piles/{id}/items/{item_id}

GET    /api/me/progress              # All reading progress
GET    /api/me/progress/{item_id}    # Progress for item
PUT    /api/me/progress/{item_id}    # Update progress

GET    /api/me/statistics            # Reading statistics

# KOReader Sync (compatible API)
POST   /api/kosync/register          # Register device
POST   /api/kosync/authorize         # Authorize device
GET    /api/kosync/progress/{hash}   # Get progress by MD5
PUT    /api/kosync/progress/{hash}   # Update progress

# OPDS Catalog
GET    /opds/                        # Root catalog
GET    /opds/new                     # Recently added
GET    /opds/popular                 # Most downloaded
GET    /opds/search                  # Search
GET    /opds/author/{id}             # Author's books
GET    /opds/series/{id}             # Series books

# Admin
GET    /api/admin/users              # List users
POST   /api/admin/users              # Create user
PUT    /api/admin/users/{id}         # Update user
DELETE /api/admin/users/{id}         # Delete user
GET    /api/admin/stats              # System statistics
GET    /api/admin/queue              # Review queue
POST   /api/admin/queue/{id}/file    # File reviewed item
POST   /api/admin/queue/{id}/skip    # Skip reviewed item
```

### Pagination
All list endpoints support:
```
GET /api/items?page=1&per_page=24&sort=title&order=asc
```

### Filtering
```
GET /api/items?author_id=123&genre=fantasy&format=epub&rating_max=PG
```

### Search
```
GET /api/items?q=mistborn+sanderson&fields=title,author,description
```

## Reader Integration

### Web Reader (Foliate-js)
- Based on same engine as Readest
- EPUB, MOBI support
- Customisable typography
- Dark/light/sepia themes
- Progress saved to database
- Bookmarks and highlights (future)

### KOReader Sync Protocol
Implement the [KOReader sync server API](https://github.com/koreader/koreader-sync-server):

```python
@router.post("/kosync/register")
async def register_device(username: str, password: str):
    # Validate credentials, return auth token

@router.put("/kosync/progress/{document_hash}")
async def update_progress(
    document_hash: str,  # MD5 of first 10KB
    progress: float,
    percentage: float,
    device: str,
    device_id: str,
):
    # Store progress, return latest
```

This enables sync with:
- KOReader on Kindle, Kobo, Android, Linux
- Any app implementing the kosync protocol

### OPDS Catalog
Standard OPDS 1.2 feed for e-reader apps:
- Navigation feeds (browse by author/series/genre)
- Acquisition feeds (download books)
- Search via OpenSearch
- Authentication via HTTP Basic

Compatible with:
- Readest
- PocketBook
- KyBook
- Moon+ Reader
- Many others

## Deployment

### Docker Compose
```yaml
services:
  web:
    build: ./web
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
      - AUTH_MODE=local
    volumes:
      - library:/library:ro
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:17-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data
```

### Reverse Proxy (Traefik)
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.alexandria.rule=Host(`books.example.com`)"
  - "traefik.http.routers.alexandria.middlewares=authelia@docker"
```

### Environment Variables
```bash
# Core
ALEXANDRIA_DATABASE_URL=postgresql://user:pass@host/db
ALEXANDRIA_REDIS_URL=redis://localhost:6379
ALEXANDRIA_SECRET_KEY=your-secret-key
ALEXANDRIA_LIBRARY_ROOT=/library

# Auth
ALEXANDRIA_AUTH_MODE=local  # local, forward_auth, oidc
ALEXANDRIA_FORWARD_AUTH_USER_HEADER=X-Forwarded-User
ALEXANDRIA_FORWARD_AUTH_ADMIN_GROUP=admins

# Features
ALEXANDRIA_ENABLE_REGISTRATION=false
ALEXANDRIA_GUEST_ACCESS=false
ALEXANDRIA_KOSYNC_ENABLED=true
ALEXANDRIA_OPDS_ENABLED=true
```

## Development Phases

### Phase 1: Core API + Basic UI (MVP)
- FastAPI backend with core endpoints
- Local authentication
- Basic SvelteKit UI: browse, search, detail, download
- Mobile-friendly in-browser EPUB reader with progress sync
- Docker deployment

### Phase 2: Piles + OPDS
- User piles (To Read, Reading, Finished, custom)
- OPDS catalog for third-party reader apps
- Reading statistics

### Phase 3: Enhanced Auth + Admin
- Forward auth (Authelia) support
- Admin dashboard
- User management
- Metadata editing

### Phase 4: Polish + Extras
- Collections with access control
- Age ratings
- PWA features (offline reading, add to home screen)
- KOReader sync API (for e-ink devices)
- OIDC support

## File Structure

```
web/
├── backend/
│   ├── alexandria/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── auth/
│   │   │   ├── local.py         # Local auth
│   │   │   ├── forward.py       # Forward auth
│   │   │   └── dependencies.py  # Auth dependencies
│   │   ├── api/
│   │   │   ├── items.py
│   │   │   ├── authors.py
│   │   │   ├── series.py
│   │   │   ├── shelves.py
│   │   │   ├── progress.py
│   │   │   ├── kosync.py
│   │   │   └── admin.py
│   │   ├── opds/
│   │   │   └── catalog.py
│   │   └── models/
│   │       ├── user.py
│   │       ├── pile.py
│   │       └── progress.py
│   ├── tests/
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte           # Home
│   │   │   ├── +layout.svelte         # App shell
│   │   │   ├── browse/
│   │   │   ├── book/[id]/
│   │   │   ├── read/[id]/
│   │   │   ├── search/
│   │   │   ├── piles/
│   │   │   └── admin/
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   ├── stores/
│   │   │   └── api.ts
│   │   └── app.css
│   ├── static/
│   ├── package.json
│   ├── svelte.config.js
│   └── tailwind.config.js
│
└── docker-compose.yml
```

## References

- [Calibre-web](https://github.com/janeczku/calibre-web) - Simple, effective book UI
- [Immich](https://github.com/immich-app/immich) - Auth patterns, modern self-hosted
- [Audiobookshelf](https://github.com/advplyr/audiobookshelf) - Progress tracking, series grouping
- [KOReader Sync Server](https://github.com/koreader/koreader-sync-server) - Sync protocol
- [Foliate-js](https://github.com/johnfactotum/foliate-js) - EPUB reader engine
- [BookLore](https://github.com/booklore-app/booklore) - Modern self-hosted alternative
