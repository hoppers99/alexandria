# Roadmap

This document tracks planned features, improvements, and future ideas for Alexandria.

## Current Status

The core cataloguing pipeline and web UI are functional. Key features working:

- File ingestion via `.returns/` folder with metadata extraction
- Enrichment from Google Books, Open Library, OCLC
- DDC classification with confidence thresholds
- Review queue for manual classification
- Library browsing (authors, series, recent)
- Piles (collections) for organising reading lists
- In-browser e-book reader (EPUB, MOBI, etc.)
- Item metadata editing and enrichment

## Near-term Priorities

### Cover Management

**Status**: Complete

Users can now update covers for existing items:
- [x] Search for covers from external sources (Google Books, Open Library)
- [x] "Use this cover" button on search results
- [x] Upload custom cover images
- [x] `POST /api/items/{id}/cover` endpoint
- [x] New "Cover" tab in book edit modal

### Background/Backdrop Images

**Status**: Idea

Similar to Plex, display backdrop images on author or series pages for visual appeal.

- [ ] Research image sources (author photos, themed backgrounds)
- [ ] Add backdrop_url field to relevant models
- [ ] UI implementation for author/series pages

### Book Samples

**Status**: Idea

Allow users to preview the first chapter without downloading the full file.

- [ ] Extract first N pages/chapters during ingestion
- [ ] Store samples separately or as cached extracts
- [ ] Sample viewer in web UI

## Medium-term

### Component Refactoring

**Status**: Complete

The review page now uses shared components, reducing code duplication:

- [x] Refactor review page to use `MetadataForm` component
- [x] Refactor review page to use `SearchPanel` component
- [x] Refactor review page to use `Lightbox` component
- [x] Reduced review page from ~1200 lines to ~600 lines

### OPDS Feed

**Status**: Planned (see [features.md](features.md))

Standard catalogue format for e-reader apps (Moon+ Reader, KOReader, etc.).

- [ ] Implement OPDS 1.2 feed endpoints
- [ ] Browse by author, series, recent
- [ ] Search support
- [ ] Download links with authentication

### Watch Folder

**Status**: Planned

Automatically process files dropped into `.returns/` without manual trigger.

- [ ] Background worker/daemon to watch folder
- [ ] Configurable polling interval or filesystem events
- [ ] Notification on new items processed

## Long-term / Future Ideas

### Format Conversion

Currently out of scope (use Calibre), but could be useful:
- Convert on download (e.g., EPUB → MOBI for Kindle)
- Store multiple formats generated from source

### Reading Progress Sync

Track reading position across devices:
- Store reading progress per user per item
- Sync with e-reader apps via OPDS extensions
- "Continue reading" feature in web UI

### Recommendations

Suggest related items based on:
- DDC classification proximity
- Shared authors/series
- User reading history
- Tags/subjects overlap

### Audio/Video Support

The architecture supports mixed media but current focus is e-books:
- Audiobook support (chapters, streaming)
- Video tutorials/courses
- Podcasts/periodicals

### Multi-user Improvements

- User permissions (admin, librarian, patron roles)
- Per-user reading history and collections
- Family sharing / household accounts

## Non-Goals

These are explicitly out of scope:

- **DRM handling** - Alexandria works with DRM-free files only
- **Purchase/acquisition** - Not a storefront or download manager
- **Social features** - No reviews, ratings, or community recommendations
- **Device sync** - Use Calibre for syncing to e-readers (though OPDS helps)

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to get involved. Feature requests and pull requests welcome!
