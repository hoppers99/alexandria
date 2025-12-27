# Schema Version History

This document tracks database schema changes across Alexandria releases.

## Version Mapping

| App Version | Schema Revision | Migration | Description |
|-------------|-----------------|-----------|-------------|
| 1.0.0       | `b2640a924996` | add_sessions_table | Add user authentication and session management |
| 0.1.0       | `75b0e362b398` | initial_schema | Initial database schema with items, files, creators, collections |

## Release Details

### v1.0.0 - Authentication & Backup (2025-01-XX)

**Schema Changes:**
- Added `sessions` table for user session management
- Schema revision: `b2640a924996`

**Migrations:**
- `b2640a924996_add_sessions_table.py` - Session tracking for authentication

**Upgrade Path:**
- From v0.1.0: Automatic (1 migration)
- From fresh install: Automatic (all migrations)

**Features:**
- Multi-user authentication with username/password
- Admin and user roles
- Session-based auth with secure cookies
- Argon2id password hashing
- Auto-admin creation from environment variables
- Database backup/restore CLI commands
- Automatic database initialization on first run

**Breaking Changes:**
- None (backward compatible with v0.1.0 data)

---

### v0.1.0 - Initial Release (2025-12-XX)

**Schema Changes:**
- Initial database schema
- Schema revision: `75b0e362b398`

**Tables Created:**
- `classifications` - DDC classification codes
- `creators` - Authors, narrators, editors, etc.
- `items` - Core catalogue items
- `files` - Physical files for items
- `item_creators` - Many-to-many relationship
- `users` - User accounts (placeholder)
- `collections` - User collections/piles
- `collection_items` - Items in collections
- `source_files` - Migration tracking
- `reading_progress` - Reading progress tracking

**Features:**
- Book cataloguing and metadata management
- DDC classification system
- Multi-format support (EPUB, PDF, MOBI, etc.)
- Cover image management
- Series tracking
- Full-text search
- Migration tools for existing libraries

---

## Migration Files

All migration files are stored in `alembic/versions/`:

```
alembic/versions/
├── 75b0e362b398_initial_schema.py                      # v0.1.0
├── 2667f47d7311_drop_classification_foreign_key.py    # v0.1.0 (patch)
├── ce410afb8eee_restore_classification_fk_with_data.py # v0.1.0 (patch)
├── 368ec4f939ff_add_reading_progress.py               # v0.1.0 (feature)
├── c1fc57423096_add_system_piles.py                   # v0.1.0 (feature)
├── b2640a924996_add_sessions_table.py                 # v1.0.0
└── (more added with each release)
```

## Checking Your Schema Version

### Via CLI
```bash
# Inside Docker container
docker exec alexandria-backend uv run alembic current

# On host
uv run alembic current
```

### Via Database
```sql
SELECT version_num FROM alembic_version;
```

### Via Logs
On startup, Alexandria logs:
```
App version: 1.0.0
Current schema version: b2640a924996
Required schema version: b2640a924996 (Add sessions and auth)
Schema compatibility: ✓ Schema version matches app version
```

## Upgrade Process

### Automatic (Recommended)

Alexandria automatically upgrades the schema on startup:

```bash
# Pull new version
git pull

# Rebuild and restart
docker compose up -d --build

# Check logs
docker compose logs backend | grep schema

# Output:
# App version: 1.0.0
# Current schema version: 75b0e362b398
# Required schema version: b2640a924996
# Running upgrade 75b0e362b398 -> b2640a924996, add_sessions_table
# ✓ Database migrations completed successfully
```

### Manual (Advanced)

If you need to upgrade manually:

```bash
# See pending migrations
docker exec alexandria-backend uv run alembic current
docker exec alexandria-backend uv run alembic heads

# Upgrade to latest
docker exec alexandria-backend uv run alembic upgrade head

# Upgrade to specific version
docker exec alexandria-backend uv run alembic upgrade b2640a924996
```

## Downgrade Process

⚠️ **Warning:** Downgrading can cause data loss! Always backup first.

```bash
# Backup database
docker exec alexandria-backend uv run librarian backup /tmp/backup.dump

# Downgrade one migration
docker exec alexandria-backend uv run alembic downgrade -1

# Downgrade to specific version
docker exec alexandria-backend uv run alembic downgrade 75b0e362b398

# Restore if needed
docker exec alexandria-backend uv run librarian restore /tmp/backup.dump
```

## Version Compatibility Matrix

| App Version | Minimum Schema | Maximum Schema | Auto-Upgrade |
|-------------|----------------|----------------|--------------|
| 1.0.0       | `75b0e362b398` | `b2640a924996` | ✅ Yes       |
| 0.1.0       | `75b0e362b398` | `75b0e362b398` | ✅ Yes       |

## Adding New Schema Changes

When adding a new migration:

1. **Create migration:**
   ```bash
   uv run alembic revision -m "descriptive_name"
   ```

2. **Implement upgrade/downgrade:**
   ```python
   # In alembic/versions/xxxx_descriptive_name.py
   def upgrade() -> None:
       op.create_table('new_table', ...)

   def downgrade() -> None:
       op.drop_table('new_table')
   ```

3. **Test:**
   ```bash
   uv run alembic upgrade head    # Test upgrade
   uv run alembic downgrade -1    # Test downgrade
   uv run alembic upgrade head    # Re-apply
   ```

4. **Update this document:**
   - Add migration to version mapping table
   - Document what changed
   - Note any breaking changes
   - Update `src/web/schema_version.py` SCHEMA_VERSION_MAP

5. **Tag release:**
   ```bash
   git add alembic/versions/xxxx_descriptive_name.py
   git add SCHEMA_VERSIONS.md src/web/schema_version.py
   git commit -m "Add new_feature migration for v0.3.0"
   git tag v0.3.0
   ```

## Schema Design Principles

1. **Backward Compatibility:** Prefer additive changes (new tables/columns)
2. **Data Preservation:** Never drop columns with data without migration path
3. **Idempotency:** Migrations should be safe to run multiple times
4. **Transactions:** Each migration runs in a transaction
5. **Documentation:** Always document breaking changes

## Troubleshooting

### "Schema version mismatch"

**Symptoms:**
```
Current schema version: 75b0e362b398
Required schema version: b2640a924996
```

**Solution:**
```bash
# Restart to trigger automatic upgrade
docker compose restart backend

# Or manually upgrade
docker exec alexandria-backend uv run alembic upgrade head
```

### "Multiple heads in alembic"

**Symptoms:**
```
ERROR: Multiple heads are present
```

**Cause:** Merge conflict in migrations

**Solution:**
```bash
# Create a merge migration
docker exec alexandria-backend uv run alembic merge -m "merge_branches"
docker exec alexandria-backend uv run alembic upgrade head
```

### "Database already at head"

**Symptoms:**
```
INFO: Database is already at head revision
```

**Solution:** This is normal! Your database is up to date.

## See Also

- [Database Schema Documentation](docs/schema.md) - Complete schema reference
- [Backup & Restore Guide](docs/backup-restore.md) - Data protection
- [Initialization Guide](docs/initialization.md) - First-time setup
