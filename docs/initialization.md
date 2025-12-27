# Database Initialization

## Automatic Initialization on First Run

Alexandria automatically initializes itself on first startup. **No manual database setup is required!**

## What Happens on First Run

When you start Alexandria for the first time (`docker compose up -d` or `uv run python -m web.main`), the following happens automatically:

### 1. Database Migrations (Schema Creation)
```
✓ Database migrations completed successfully
```

The backend automatically runs all Alembic migrations to create the database schema:
- Creates all tables (items, files, creators, users, sessions, etc.)
- Sets up indexes for performance
- Configures full-text search
- Establishes foreign key relationships

**Technical details:**
- Uses `alembic upgrade head` under the hood
- Runs on every startup (safe - only applies new migrations)
- Location: `src/web/startup.py:run_database_migrations()`

### 2. Initial Data Seeding
```
✓ Seeded 1000 classification codes
```

Seeds the database with essential reference data:
- **DDC Classification Codes**: Dewey Decimal Classification system (000-999)
- Top-level categories (100s)
- Mid-level categories (10s)
- Specific categories (1s)

**Technical details:**
- Only runs if classifications table is empty
- Idempotent (safe to run multiple times)
- Location: `librarian/db/seed.py:seed_classifications()`

### 3. Admin User Creation (if configured)
```
✓ Created initial admin user: admin (ID: 1)
```

If environment variables are set and no users exist:
- Creates admin user with provided credentials
- Sets `is_admin=True` flag
- Ready for immediate login

**Environment variables:**
```bash
ALEXANDRIA_ADMIN_USERNAME=admin
ALEXANDRIA_ADMIN_PASSWORD=your-secure-password
ALEXANDRIA_ADMIN_EMAIL=admin@example.com  # optional
```

**Technical details:**
- Only creates if `users` table is empty
- Safe to leave env vars set (won't create duplicate users)
- Location: `src/web/auth/startup.py:create_initial_admin()`

### 4. Web Server Start
```
Starting Alexandria Web UI...
Startup tasks completed
INFO:     Uvicorn running on http://0.0.0.0:8000
```

FastAPI/Uvicorn web server starts and begins accepting requests.

## Subsequent Starts

On subsequent starts, Alexandria:
1. ✅ Checks for new migrations (applies if any)
2. ⏭️ Skips seeding (data already exists)
3. ⏭️ Skips admin creation (users already exist)
4. ✅ Starts web server

**Result:** Fast startup (~1-2 seconds)

## Manual Initialization (Not Recommended)

If you prefer to run steps manually:

```bash
# 1. Run migrations
docker exec alexandria-backend uv run alembic upgrade head

# 2. Seed classifications
docker exec alexandria-backend uv run librarian seed

# 3. Create admin user
docker exec alexandria-backend uv run librarian create-admin

# 4. Start server
docker compose up -d backend
```

**Note:** With auto-initialization, you never need to do this!

## Verification

Check that initialization succeeded:

```bash
# View startup logs
docker compose logs backend | grep -E "migrations|Seeded|Created initial"

# Expected output:
# ✓ Database migrations completed successfully
# ✓ Seeded 1000 classification codes
# ✓ Created initial admin user: admin (ID: 1)
```

Or check the database directly:

```bash
# Count tables
docker exec alexandria-postgres psql -U alexandria -d alexandria -c "\dt" | wc -l
# Should show 10+ tables

# Count classifications
docker exec alexandria-postgres psql -U alexandria -d alexandria -c "SELECT COUNT(*) FROM classifications;"
# Should show ~1000

# Count users
docker exec alexandria-postgres psql -U alexandria -d alexandria -c "SELECT COUNT(*) FROM users;"
# Should show 1 (if admin was created)
```

## Troubleshooting

### "Database migration failed"

**Cause:** PostgreSQL not ready yet or network issue

**Solution:**
```bash
# Wait for PostgreSQL to be healthy
docker compose ps postgres
# Should show "healthy"

# Manually run migrations
docker exec alexandria-backend uv run alembic upgrade head

# Restart backend
docker compose restart backend
```

### "alembic command not found"

**Cause:** Dockerfile built without dependencies

**Solution:**
```bash
# Rebuild with dependencies
docker compose build --no-cache backend
docker compose up -d
```

### "No users exist and ALEXANDRIA_ADMIN_USERNAME not set"

**Cause:** Admin env vars not configured

**Solution - Option 1 (Environment variables):**
```bash
# Add to .env or docker-compose.yml
ALEXANDRIA_ADMIN_USERNAME=admin
ALEXANDRIA_ADMIN_PASSWORD=secure-password

# Restart
docker compose down
docker compose up -d
```

**Solution - Option 2 (Manual creation):**
```bash
docker exec -it alexandria-backend uv run librarian create-admin
```

### "Username already exists"

**Cause:** Admin user already created

**Solution:** This is normal! Just login with existing credentials or:
```bash
# Create a different admin user
docker exec -it alexandria-backend uv run librarian create-admin
# Use a different username
```

### Database already initialized but want to start fresh

```bash
# WARNING: This deletes all data!

# Stop services
docker compose down

# Delete database volume
rm -rf ./data/postgres

# Start fresh
docker compose up -d
# Database will be re-initialized automatically
```

## Migration Files

All migrations are stored in `alembic/versions/`:
```
alembic/versions/
├── 75b0e362b398_initial_schema.py
├── 2667f47d7311_drop_classification_foreign_key.py
├── ce410afb8eee_restore_classification_fk_with_data.py
├── 368ec4f939ff_add_reading_progress.py
├── c1fc57423096_add_system_piles.py
├── b2640a924996_add_sessions_table.py
└── ... (more as they're added)
```

Each migration:
- Has an upgrade() function (applies changes)
- Has a downgrade() function (reverts changes)
- Is versioned and ordered
- Is idempotent (safe to run multiple times)

## Environment Variables for Initialization

```bash
# Database connection (required)
ALEXANDRIA_DB_HOST=postgres
ALEXANDRIA_DB_PORT=5432
ALEXANDRIA_DB_NAME=alexandria
ALEXANDRIA_DB_USER=alexandria
ALEXANDRIA_DB_PASSWORD=alexandria

# Auto-admin creation (optional, recommended)
ALEXANDRIA_ADMIN_USERNAME=admin
ALEXANDRIA_ADMIN_PASSWORD=changeme
ALEXANDRIA_ADMIN_EMAIL=admin@example.com
```

## Best Practices

1. ✅ **Use auto-initialization** - Let Alexandria handle setup
2. ✅ **Set admin env vars** - Easier than manual CLI
3. ✅ **Check startup logs** - Verify initialization succeeded
4. ✅ **Change default password** - After first login
5. ✅ **Backup after setup** - Before adding library data

## For Developers

### Adding New Migrations

```bash
# Create new migration
uv run alembic revision -m "add_new_feature"

# Edit the generated file in alembic/versions/

# Test upgrade
uv run alembic upgrade head

# Test downgrade
uv run alembic downgrade -1
```

### Disabling Auto-Initialization

If you need to disable auto-initialization for testing:

```python
# In src/web/main.py, comment out:
# run_startup_tasks(db)

# Or set environment variable:
ALEXANDRIA_SKIP_STARTUP_TASKS=true
```

(Note: This feature would need to be implemented)

## See Also

- [Database Schema](schema.md) - Complete schema documentation
- [Authentication Guide](authentication.md) - User management
- [Deployment Quick Start](../DEPLOYMENT_QUICK_START.md) - Full deployment guide
- [Backup & Restore](backup-restore.md) - Data protection
