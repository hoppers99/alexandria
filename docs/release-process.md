# Release Process

This document describes how to create a new release of Alexandria with proper version and schema management.

## Pre-Release Checklist

- [ ] All features tested locally
- [ ] Database migrations tested (upgrade and downgrade)
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Schema version mapping updated (if schema changed)
- [ ] Breaking changes documented
- [ ] Backup/restore tested with new schema

## Release Steps

### 1. Update Version Numbers

**Update `src/librarian/__init__.py`:**
```python
__version__ = "1.0.0"
```

**Update `src/web/__init__.py`:**
```python
__version__ = "1.0.0"
```

**Update `pyproject.toml`:**
```toml
[project]
version = "1.0.0"
```

### 2. Update Schema Version Map (If Schema Changed)

**Edit `src/web/schema_version.py`:**
```python
SCHEMA_VERSION_MAP = {
    "0.1.0": SchemaVersion("75b0e362b398", "Initial schema"),
    "1.0.0": SchemaVersion("b2640a924996", "Add sessions and auth"),
    "0.3.0": SchemaVersion("xxxxxxxxxxxxx", "Your new feature"),  # Add this
}
```

### 3. Update Documentation

**Update `SCHEMA_VERSIONS.md`:**
- Add new version to the version mapping table
- Add release details section
- Document any breaking changes
- List new migrations

**Update `CHANGELOG.md`:**
```markdown
## [0.3.0] - 2025-02-01

### Added
- New feature X
- New feature Y

### Changed
- Improved Z

### Database Changes
- Migration `xxxxxxxxxxxxx`: Description
```

**Update README if needed:**
- New features
- Changed requirements
- Updated screenshots

### 4. Run Pre-Release Tests

```bash
# Test migrations
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head

# Test backup/restore with new schema
uv run librarian backup /tmp/test_backup.dump
# Wipe database
dropdb alexandria && createdb alexandria
# Restore
uv run librarian restore /tmp/test_backup.dump

# Test auto-initialization
docker compose down -v
docker compose up -d
docker compose logs backend | grep -E "schema|migration|Seeded|Created"

# Run test suite
uv run pytest
```

### 5. Create Release Commit

```bash
# Stage all changes
git add src/librarian/__init__.py
git add src/web/__init__.py
git add pyproject.toml
git add src/web/schema_version.py
git add SCHEMA_VERSIONS.md
git add CHANGELOG.md
git add alembic/versions/*.py  # If new migrations

# Commit
git commit -m "Release v0.3.0

- Add feature X
- Add feature Y
- Schema migration: xxxxxxxxxxxxx (description)

Breaking changes: None
"
```

### 6. Tag Release

```bash
# Create annotated tag
git tag -a v0.3.0 -m "Release v0.3.0

Features:
- New feature X
- New feature Y

Schema changes:
- Migration xxxxxxxxxxxxx: Description

Upgrade from v1.0.0: Automatic (1 migration)
"

# Push tag
git push origin v0.3.0
```

### 7. Build and Push Docker Images

```bash
# Build multi-platform images
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/yourusername/alexandria:0.3.0 \
  -t ghcr.io/yourusername/alexandria:latest \
  --push .

# Build frontend (if separate)
cd frontend
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/yourusername/alexandria-frontend:0.3.0 \
  --push .
```

### 8. Create GitHub Release

1. Go to GitHub → Releases → "Draft a new release"
2. Choose tag: `v0.3.0`
3. Title: `Alexandria v0.3.0`
4. Description (from CHANGELOG):
   ```markdown
   ## What's New

   - New feature X
   - New feature Y

   ## Database Changes

   This release includes schema migration `xxxxxxxxxxxxx`.
   **The database will be automatically upgraded on first startup.**

   No manual migration steps required!

   ## Upgrade Instructions

   **Docker:**
   ```bash
   docker compose pull
   docker compose up -d
   ```

   **From Source:**
   ```bash
   git pull
   git checkout v0.3.0
   docker compose up -d --build
   ```

   ## Breaking Changes

   None

   ## Full Changelog

   [See CHANGELOG.md](CHANGELOG.md)
   ```

5. Attach any binaries/assets
6. Check "Create a discussion for this release" if desired
7. Publish release

### 9. Post-Release Tasks

- [ ] Update documentation site (if exists)
- [ ] Announce on Discord/Reddit/forum
- [ ] Close related GitHub issues
- [ ] Update Unraid template (if applicable)
- [ ] Tweet/social media announcement
- [ ] Monitor for issues

## Hotfix Release Process

For urgent fixes between releases:

### 1. Create Hotfix Branch

```bash
git checkout v1.0.0
git checkout -b hotfix/0.2.1
```

### 2. Make Fix

```bash
# Fix the issue
# Update version to 0.2.1
# Commit fix
```

### 3. Release Hotfix

```bash
git tag -a v0.2.1 -m "Hotfix v0.2.1: Fix critical bug"
git push origin v0.2.1
git checkout main
git merge hotfix/0.2.1
git push
```

## Schema Migration Releases

When releasing with schema changes, extra care is needed:

### Before Release

1. **Test upgrade path:**
   ```bash
   # From each previous version
   docker compose down -v
   # Restore v1.0.0 database backup
   docker exec alexandria-backend uv run librarian restore backup_v1.0.0.dump
   # Start v0.3.0
   docker compose up -d
   # Verify upgrade succeeded
   ```

2. **Test downgrade path:**
   ```bash
   docker exec alexandria-backend uv run alembic downgrade -1
   # Verify app still works
   docker exec alexandria-backend uv run alembic upgrade head
   ```

3. **Document data migrations:**
   - If migration transforms data, document the transformation
   - Test with realistic data volumes
   - Time the migration for large databases

### During Release

**In release notes, clearly state:**
- Schema version is changing
- Automatic upgrade will occur
- Estimated migration time
- Backup recommendation
- Rollback procedure if needed

**Example:**
```markdown
## ⚠️ Database Migration Required

This release includes a schema migration that will run automatically on startup.

**Migration:** `xxxxxxxxxxxxx_add_new_table.py`
**Estimated time:** < 1 second for small libraries, ~5 seconds for 10,000+ books
**Recommendation:** Backup your database before upgrading

### Backup Before Upgrade

```bash
docker exec alexandria-backend uv run librarian backup /backups/pre_v0.3.0.dump
```

### Rollback If Needed

```bash
docker compose down
# Restore old version
git checkout v1.0.0
docker compose up -d --build
# Restore backup
docker exec alexandria-backend uv run librarian restore /backups/pre_v0.3.0.dump
```
```

## Version Numbering

Alexandria follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (x.0.0): Incompatible API changes, major schema restructure
- **MINOR** (0.x.0): New features, backward-compatible schema changes
- **PATCH** (0.0.x): Bug fixes, no schema changes

**Schema changes:**
- New tables/columns: MINOR version bump
- Removed tables/columns: MAJOR version bump (breaking)
- Index changes: PATCH version bump
- Data migrations: MINOR or MAJOR depending on impact

## Testing Matrix

Test these scenarios before release:

| Scenario | Test |
|----------|------|
| Fresh install | `docker compose up -d` from scratch |
| Upgrade from previous | Restore v(n-1) backup, start v(n) |
| Upgrade skipping version | Restore v(n-2) backup, start v(n) |
| Downgrade | `alembic downgrade -1` |
| Large database | Test with 10,000+ items |
| Migration failure | Simulate error, verify rollback |
| Backup/restore | Round-trip with new schema |

## Rollback Plan

If a release causes issues:

1. **Immediate rollback:**
   ```bash
   # Stop services
   docker compose down

   # Checkout previous version
   git checkout v1.0.0

   # Restore previous database
   docker exec alexandria-backend uv run librarian restore backup.dump

   # Start old version
   docker compose up -d --build
   ```

2. **Announce rollback:**
   - Update GitHub release with warning
   - Post on communication channels
   - Create hotfix if possible

3. **Fix and re-release:**
   - Fix the issue
   - Increment patch version (0.3.1)
   - Re-test thoroughly
   - Release with "fixes v0.3.0 issues" notice

## Release Checklist Template

Copy this for each release:

```markdown
# Release vX.X.X Checklist

## Pre-Release
- [ ] Version numbers updated (3 files)
- [ ] Schema version map updated (if needed)
- [ ] SCHEMA_VERSIONS.md updated
- [ ] CHANGELOG.md updated
- [ ] Migration tested (upgrade + downgrade)
- [ ] Backup/restore tested
- [ ] Fresh install tested
- [ ] Test suite passing
- [ ] Documentation reviewed

## Release
- [ ] Release commit created
- [ ] Tag created and pushed
- [ ] Docker images built and pushed
- [ ] GitHub release published
- [ ] Release notes complete

## Post-Release
- [ ] Monitor for issues (24-48 hours)
- [ ] Update external documentation
- [ ] Announce release
- [ ] Close related issues
- [ ] Plan next release
```

## Emergency Procedures

### Critical Bug in Production

1. Create hotfix branch immediately
2. Fix bug
3. Fast-track testing
4. Release as patch version
5. Notify all users

### Data Loss Bug

1. **STOP DEPLOYMENTS IMMEDIATELY**
2. Post prominent warning on GitHub
3. Provide data recovery instructions
4. Fix bug
5. Test exhaustively
6. Release with detailed upgrade guide

### Schema Corruption

1. Document the corruption pattern
2. Create migration to fix corrupted data
3. Test with affected databases
4. Release with automatic fix + manual recovery guide

## See Also

- [SCHEMA_VERSIONS.md](../SCHEMA_VERSIONS.md) - Schema version history
- [CHANGELOG.md](../CHANGELOG.md) - Release history
- [Contributing Guide](contributing.md) - Development workflow
