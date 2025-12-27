# Backup and Restore Guide

## Overview

Alexandria provides comprehensive backup and restore capabilities for both the database (metadata) and library files (books, covers, etc.). This guide covers best practices for both scenarios.

## Database Backup (Essential)

The database contains all metadata, user accounts, reading progress, collections, and cataloguing information. **This should be backed up regularly.**

### Prerequisites

PostgreSQL client tools must be installed:
- **macOS**: `brew install postgresql` or use Postgres.app
- **Linux**: `apt install postgresql-client` or `yum install postgresql`
- **Docker**: PostgreSQL tools are included in the librarian container

### Creating a Database Backup

```bash
# Basic backup (recommended)
uv run librarian backup alexandria_backup_$(date +%Y%m%d).dump

# SQL format (more portable, larger file size)
uv run librarian backup --format sql alexandria_backup.sql

# Maximum compression
uv run librarian backup --compress 9 alexandria_backup.dump
```

### Restoring a Database Backup

```bash
# Restore from backup
uv run librarian restore alexandria_backup.dump

# Restore with confirmation skip
uv run librarian restore --yes alexandria_backup.dump

# Clean restore (drop existing objects first)
uv run librarian restore --clean alexandria_backup.dump
```

**⚠️ Warning**: Restore will overwrite the current database. Make sure to back up first!

### Automated Database Backups

Set up a cron job for regular backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM, keep last 7 days
0 2 * * * cd /path/to/alexandria && uv run librarian backup backups/db_$(date +\%Y\%m\%d).dump && find backups/ -name "db_*.dump" -mtime +7 -delete
```

### Backup File Sizes

Typical database sizes:
- **Small library** (1,000 books): ~10-20 MB
- **Medium library** (10,000 books): ~100-200 MB
- **Large library** (100,000 books): ~1-2 GB

The custom format (`.dump`) uses compression and is recommended for regular backups.

## Library Files Backup (Optional but Recommended)

The library files include all books, covers, and media. These are typically much larger than the database.

### Strategy 1: rsync (Recommended for Large Libraries)

`rsync` provides efficient incremental backups by only copying changed files.

```bash
# Initial full backup
rsync -av --progress \
  /path/to/library/ \
  /path/to/backup/library/

# Incremental backup (only copies changes)
rsync -av --progress --delete \
  /path/to/library/ \
  /path/to/backup/library/

# Remote backup via SSH
rsync -av --progress \
  /path/to/library/ \
  user@backup-server:/backups/alexandria/library/
```

**Advantages**:
- Very fast incremental updates
- Preserves file permissions and timestamps
- Can resume interrupted transfers
- Works over SSH for remote backups

**Disadvantages**:
- No deduplication (duplicate books stored separately)
- No compression
- No encryption (unless using SSH)

### Strategy 2: Restic (Recommended for Production)

[Restic](https://restic.net/) provides encrypted, deduplicated, compressed backups with versioning.

```bash
# Install restic
brew install restic  # macOS
apt install restic   # Linux

# Initialize repository
restic init --repo /path/to/backup/repo

# Create backup
restic backup /path/to/library --repo /path/to/backup/repo

# Restore specific snapshot
restic restore latest --target /path/to/restore --repo /path/to/backup/repo

# List snapshots
restic snapshots --repo /path/to/backup/repo

# Automatic cleanup (keep last 7 daily, 4 weekly, 12 monthly)
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune --repo /path/to/backup/repo
```

**Advantages**:
- Deduplication saves space (duplicate files stored once)
- Built-in compression
- Encryption at rest
- Supports multiple backends (local, S3, B2, etc.)
- Versioned snapshots

**Disadvantages**:
- Slightly more complex setup
- Requires learning restic commands

### Strategy 3: Borg Backup (Linux/macOS)

[BorgBackup](https://www.borgbackup.org/) is similar to restic, with excellent deduplication.

```bash
# Install borg
brew install borgbackup  # macOS
apt install borgbackup   # Linux

# Initialize repository
borg init --encryption=repokey /path/to/backup/repo

# Create backup
borg create /path/to/backup/repo::$(date +%Y%m%d) /path/to/library

# List archives
borg list /path/to/backup/repo

# Restore
borg extract /path/to/backup/repo::20250127

# Prune old backups
borg prune --keep-daily=7 --keep-weekly=4 --keep-monthly=12 /path/to/backup/repo
```

### Strategy 4: Cloud Storage Sync

For cloud backups, use tools like:
- **rclone**: Syncs to any cloud storage (S3, Google Drive, Dropbox, etc.)
- **Nextcloud**: Self-hosted cloud with sync clients
- **Syncthing**: P2P continuous synchronisation

Example with rclone to Backblaze B2:

```bash
# Configure backend (once)
rclone config

# Sync to cloud
rclone sync /path/to/library b2:alexandria-backup/library --progress
```

## Complete Backup Strategy (Recommended)

### Daily: Database Only
```bash
# Fast, small backups
uv run librarian backup backups/daily/db_$(date +%Y%m%d).dump
```

### Weekly: Database + Library Files
```bash
# Full backup with restic
restic backup /path/to/library --repo /path/to/backup/repo
uv run librarian backup backups/weekly/db_$(date +%Y%m%d).dump
```

### Monthly: Offsite Copy
```bash
# Copy to cloud storage
rclone sync /path/to/backup/repo remote:alexandria-backups
```

## Library Size Considerations

Large libraries present unique challenges:

### Typical Sizes

| Library Size | Files | Storage | Backup Time (rsync) | Backup Time (restic) |
|--------------|-------|---------|---------------------|----------------------|
| Small        | 1K    | 10 GB   | 5-10 min            | 10-15 min (first)    |
| Medium       | 10K   | 100 GB  | 30-60 min           | 1-2 hours (first)    |
| Large        | 100K  | 1 TB    | 5-8 hours           | 8-12 hours (first)  |

**Note**: Incremental backups with rsync/restic are much faster (minutes instead of hours).

### Optimisation Strategies

1. **Separate Backup Schedules**
   - Database: Daily (fast, small)
   - Library files: Weekly (slow, large)
   - Critical: After major changes

2. **Deduplication**
   - Use restic/borg to deduplicate identical files
   - Can save 20-40% space if you have duplicate editions

3. **Exclude Unnecessary Files**
   - Backup source files in `.returns/` separately or exclude
   - Exclude temporary/cache files

4. **Bandwidth Considerations**
   - For remote backups, use compression
   - Consider incremental backups to reduce transfer time
   - Use bandwidth throttling: `rsync --bwlimit=10000` (10 MB/s)

5. **Storage Planning**
   - Database: Plan for 1-2 MB per 100 books
   - Files: Plan for 5-10 MB per book (mixed formats)
   - Backups: 1.5x library size (with versioning/snapshots)

## Disaster Recovery

### Scenario 1: Database Corruption

If only the database is corrupted but files are intact:

```bash
# Restore database
uv run librarian restore --clean latest_backup.dump

# Restart web server
docker compose restart web
```

### Scenario 2: Complete Server Loss

If moving to a new server:

```bash
# 1. Install Alexandria and dependencies
git clone https://github.com/yourusername/alexandria
cd alexandria

# 2. Restore database
uv run alembic upgrade head
uv run librarian restore backup.dump

# 3. Restore library files
rsync -av backup-server:/backups/library/ library/

# 4. Start services
docker compose up -d
```

### Scenario 3: Migrating Between Servers

```bash
# On old server
uv run librarian backup /tmp/alexandria.dump
rsync -av library/ new-server:/path/to/library/

# On new server
uv run librarian restore /tmp/alexandria.dump
```

## Testing Backups

**Always test your backups!** A backup you haven't tested is not a backup.

```bash
# 1. Create test restore location
mkdir -p /tmp/restore_test

# 2. Restore database to test instance
ALEXANDRIA_DB_NAME=alexandria_test uv run librarian restore backup.dump

# 3. Verify data
ALEXANDRIA_DB_NAME=alexandria_test uv run librarian check

# 4. Clean up test database
dropdb alexandria_test
```

## Backup Checklist

- [ ] Database backups automated (daily)
- [ ] Library files backed up (weekly)
- [ ] Offsite/cloud backup configured
- [ ] Backup restoration tested
- [ ] Monitoring/alerts for failed backups
- [ ] Retention policy configured
- [ ] Encryption enabled for sensitive data
- [ ] Backup integrity checks scheduled

## Additional Resources

- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [Restic Documentation](https://restic.readthedocs.io/)
- [BorgBackup Documentation](https://borgbackup.readthedocs.io/)
- [rclone Documentation](https://rclone.org/docs/)

## Troubleshooting

### pg_dump not found

Install PostgreSQL client tools:
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt install postgresql-client

# Fedora/RHEL
sudo dnf install postgresql
```

### Backup file too large

Use maximum compression:
```bash
uv run librarian backup --compress 9 backup.dump
```

Or use SQL format and compress externally:
```bash
uv run librarian backup --format sql backup.sql
gzip backup.sql
```

### Restore fails with "already exists"

Use clean restore to drop existing objects:
```bash
uv run librarian restore --clean backup.dump
```

### Permission denied during file restore

Ensure file permissions match:
```bash
chown -R alexandria:alexandria /path/to/library
chmod -R u+rwX,go+rX /path/to/library
```
