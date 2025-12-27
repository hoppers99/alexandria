# Alexandria Deployment Quick Start

## Running with Docker Compose

### 1. Set Up Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and set:
# - ALEXANDRIA_LIBRARY_ROOT (where your books are stored)
# - ALEXANDRIA_ADMIN_USERNAME (for auto-admin creation)
# - ALEXANDRIA_ADMIN_PASSWORD (for auto-admin creation)
# - ALEXANDRIA_SECRET_KEY (generate: python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 2. Start Services

```bash
# Start all services (backend, frontend, postgres)
docker compose up -d

# Check logs
docker compose logs -f backend

# On first run, you should see:
# - "App version: 1.0.0"
# - "Current schema version: Not initialized"
# - "Required schema version: b2640a924996 (Add sessions and auth)"
# - "✓ Database migrations completed successfully"
# - "✓ Seeded XXX classification codes"
# - "✓ Created initial admin user: admin (ID: 1)"
```

**What happens on first run:**
1. Version compatibility is checked
2. Database schema is automatically created via Alembic migrations
3. DDC classification codes are seeded
4. Admin user is created (if env vars are set)
5. Web server starts

**On subsequent runs:**
- Schema version is checked against app version
- New migrations are applied automatically if needed
- Server starts (fast, ~1-2 seconds)

### 3. Access Alexandria

- **Web UI**: http://localhost:5173
- **API Docs**: http://localhost:8000/api/docs
- **Backend**: http://localhost:8000

### 4. Login

Use the credentials from your environment variables:
- Username: `admin` (or your `ALEXANDRIA_ADMIN_USERNAME`)
- Password: Your `ALEXANDRIA_ADMIN_PASSWORD`

**⚠️ Important**: Change your password after first login!

## CLI Commands Inside Docker

All librarian commands can be run inside the container:

```bash
# Create admin user (if auto-creation not used)
docker exec -it alexandria-backend uv run librarian create-admin

# Backup database
docker exec alexandria-backend uv run librarian backup /tmp/backup.dump

# Copy backup out of container
docker cp alexandria-backend:/tmp/backup.dump ./backups/

# Restore database
docker cp ./backups/backup.dump alexandria-backend:/tmp/backup.dump
docker exec alexandria-backend uv run librarian restore /tmp/backup.dump

# Run migrations (only needed if you add custom migrations)
docker exec alexandria-backend uv run alembic upgrade head

# Check library stats
docker exec alexandria-backend uv run librarian migrate status

# Process files in .returns folder
docker exec alexandria-backend uv run librarian review
```

## Unraid Template

For Unraid deployments, you can use these container variables:

```xml
<Config Name="Admin Username" Target="ALEXANDRIA_ADMIN_USERNAME" Default="admin" Mode="" Description="Admin username (auto-created on first run)" Type="Variable" Display="always" Required="true" Mask="false"/>

<Config Name="Admin Password" Target="ALEXANDRIA_ADMIN_PASSWORD" Default="" Mode="" Description="Admin password (auto-created on first run - CHANGE AFTER FIRST LOGIN!)" Type="Variable" Display="always" Required="true" Mask="true"/>

<Config Name="Admin Email" Target="ALEXANDRIA_ADMIN_EMAIL" Default="" Mode="" Description="Admin email (optional)" Type="Variable" Display="advanced" Required="false" Mask="false"/>

<Config Name="Library Path" Target="/library" Default="/mnt/user/Books/" Mode="rw" Description="Path to your book library" Type="Path" Display="always" Required="true" Mask="false"/>

<Config Name="Database Path" Target="/var/lib/postgresql/data" Default="/mnt/user/appdata/alexandria/postgres" Mode="rw" Description="PostgreSQL database storage" Type="Path" Display="always" Required="true" Mask="false"/>

<Config Name="Secret Key" Target="ALEXANDRIA_SECRET_KEY" Default="" Mode="" Description="Secret key for session encryption (generate random string)" Type="Variable" Display="always" Required="true" Mask="true"/>
```

## Backup Strategy

### Database Backups (Essential)

```bash
# Daily backup via cron inside container
docker exec alexandria-backend sh -c "uv run librarian backup /backups/db_\$(date +%Y%m%d).dump"

# Keep last 7 days
docker exec alexandria-backend find /backups -name "db_*.dump" -mtime +7 -delete
```

### Library File Backups (Recommended)

```bash
# Using rsync (incremental, fast)
rsync -av --progress ./library/ /path/to/backup/library/

# Using restic (deduplicated, encrypted)
restic backup ./library --repo /path/to/backup/repo
```

See [docs/backup-restore.md](docs/backup-restore.md) for comprehensive backup strategies.

## Environment Variables Reference

### Essential
- `ALEXANDRIA_LIBRARY_ROOT` - Path to library folder (default: `./library`)
- `ALEXANDRIA_ADMIN_USERNAME` - Auto-create admin username
- `ALEXANDRIA_ADMIN_PASSWORD` - Auto-create admin password
- `ALEXANDRIA_SECRET_KEY` - Session encryption key (REQUIRED in production)

### Database
- `ALEXANDRIA_DB_HOST` - PostgreSQL host (default: `localhost`)
- `ALEXANDRIA_DB_PORT` - PostgreSQL port (default: `5433`)
- `ALEXANDRIA_DB_NAME` - Database name (default: `alexandria`)
- `ALEXANDRIA_DB_USER` - Database user (default: `alexandria`)
- `ALEXANDRIA_DB_PASSWORD` - Database password (default: `alexandria`)

### Authentication
- `ALEXANDRIA_SESSION_EXPIRE_MINUTES` - Session lifetime (default: `10080` = 1 week)
- `ALEXANDRIA_ENABLE_REGISTRATION` - Allow self-registration (default: `false`)
- `ALEXANDRIA_GUEST_ACCESS` - Allow unauthenticated browsing (default: `false`)

### Features
- `ALEXANDRIA_CONFIDENCE_THRESHOLD` - Auto-filing confidence (default: `0.8`)
- `ALEXANDRIA_ENABLE_OCLC` - Enable OCLC Classify API (default: `true`)
- `ALEXANDRIA_ENABLE_OPENLIBRARY` - Enable Open Library API (default: `true`)
- `ALEXANDRIA_ENABLE_GOOGLE_BOOKS` - Enable Google Books API (default: `true`)

See `.env.example` for complete list.

## Troubleshooting

### No admin user created

Check logs:
```bash
docker compose logs backend | grep admin
```

If you see "No users exist and ALEXANDRIA_ADMIN_USERNAME not set":
```bash
# Set environment variables in docker-compose.yml or .env
# Then restart:
docker compose down
docker compose up -d

# Or create manually:
docker exec -it alexandria-backend uv run librarian create-admin
```

### Database not initialized

If you see "Database migration failed" in logs:
```bash
# Check if PostgreSQL is ready
docker compose ps postgres

# Manually run migrations
docker exec alexandria-backend uv run alembic upgrade head

# Restart backend
docker compose restart backend
```

### Database connection errors

Ensure PostgreSQL is healthy:
```bash
docker compose ps postgres
docker compose logs postgres
```

### Port conflicts

If ports 5433 or 8000 are in use:
```yaml
# In docker-compose.yml, change:
ports:
  - "5434:5432"  # Different host port
```

### Permission errors on library folder

```bash
# Fix ownership (adjust user:group as needed)
chown -R 1000:1000 ./library
chmod -R u+rwX,go+rX ./library
```

## Upgrading Between Versions

Alexandria automatically handles database schema upgrades:

```bash
# 1. Backup first (always!)
docker exec alexandria-backend uv run librarian backup /backups/pre_upgrade.dump

# 2. Pull new version
git pull
# Or: docker compose pull (if using pre-built images)

# 3. Rebuild and restart
docker compose up -d --build

# 4. Check logs for successful upgrade
docker compose logs backend | grep -E "App version|schema|migration"

# You should see:
# - App version: 1.0.0
# - Current schema version: 75b0e362b398
# - Required schema version: b2640a924996
# - Running upgrade 75b0e362b398 -> b2640a924996, add_sessions_table
# - ✓ Database migrations completed successfully
```

**No manual migration steps needed!** The database automatically upgrades on startup.

See [SCHEMA_VERSIONS.md](SCHEMA_VERSIONS.md) for version history and migration details.

## Production Checklist

- [ ] Change `ALEXANDRIA_SECRET_KEY` to a secure random value
- [ ] Change admin password after first login
- [ ] Remove or secure `ALEXANDRIA_ADMIN_USERNAME`/`ALEXANDRIA_ADMIN_PASSWORD` from environment
- [ ] Set up HTTPS with reverse proxy (Traefik, nginx, Caddy)
- [ ] Enable database backups (daily)
- [ ] Enable library file backups (weekly)
- [ ] Test restore procedure
- [ ] Disable guest access if not needed
- [ ] Disable registration if not needed
- [ ] Set up monitoring/alerts

## Documentation

- [Authentication Guide](docs/authentication.md) - User management, roles, security
- [Backup & Restore Guide](docs/backup-restore.md) - Comprehensive backup strategies
- [Schema Versions](SCHEMA_VERSIONS.md) - Database schema version history and upgrades
- [Initialization Guide](docs/initialization.md) - First-time setup and auto-initialization
- [Architecture Overview](docs/architecture.md) - System design and components
- [Database Schema](docs/schema.md) - Database structure and models
- [Release Process](docs/release-process.md) - For maintainers: how to create releases

## Getting Help

- GitHub Issues: https://github.com/yourusername/alexandria/issues
- Documentation: `docs/` folder
- CLI Help: `docker exec alexandria-backend uv run librarian --help`
