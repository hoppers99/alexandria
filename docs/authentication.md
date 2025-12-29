# Authentication & User Management

> **⚠️ IMPLEMENTATION STATUS**: Authentication is currently being implemented. Backend infrastructure is complete, frontend login flow is being debugged. See [AUTH_IMPLEMENTATION_STATUS.md](./AUTH_IMPLEMENTATION_STATUS.md) for current progress.

## Overview

Alexandria supports multi-user authentication with role-based access control. Users can have either **User** or **Admin** roles.

**Current State (2025-12-28)**:
- ✅ Backend auth system fully implemented
- ✅ Piles API protected (user isolation working)
- 🔧 Frontend login UI created but debugging cookie persistence
- ⏳ Other API endpoints not yet protected
- ⏳ Rate limiting, password validation, audit logging not yet integrated

## Quick Start (Docker/Unraid)

### Auto-Admin Creation

The easiest way to set up authentication in a Docker environment is to use environment variables for auto-admin creation:

```yaml
# docker-compose.yml or Unraid template
environment:
  - ALEXANDRIA_ADMIN_USERNAME=admin
  - ALEXANDRIA_ADMIN_PASSWORD=your-secure-password
  - ALEXANDRIA_ADMIN_EMAIL=admin@example.com
```

On first startup, if no users exist, Alexandria will automatically create an admin user with these credentials.

**⚠️ Security Note**: After first login, change the password via the web UI or remove these environment variables for security.

## Manual Admin Creation

### Inside Docker Container

```bash
# Interactive creation
docker exec -it alexandria-backend uv run librarian create-admin

# Or with direct input
docker exec -it alexandria-backend uv run librarian create-admin \
  --username admin \
  --email admin@example.com
```

### On Host (Development)

```bash
# Interactive creation
uv run librarian create-admin

# The command will prompt for:
# - Username
# - Password (hidden input)
# - Email (optional)
# - Display name (optional)
```

## User Roles

### Admin
- Full access to all features
- User management
- Metadata editing
- Settings configuration
- Review queue management

### User
- Browse and search library
- Download books
- Read online
- Manage personal collections (piles)
- Track reading progress
- Rate and review books

### Guest (Optional)
- Can be enabled via `ALEXANDRIA_GUEST_ACCESS=true`
- Browse and search only
- No download, progress tracking, or collections

## Configuration

### Environment Variables

```bash
# Authentication mode
ALEXANDRIA_AUTH_MODE=local                    # local, forward_auth, or both

# Session settings
ALEXANDRIA_SECRET_KEY=your-secret-key         # CHANGE IN PRODUCTION!
ALEXANDRIA_SESSION_EXPIRE_MINUTES=10080       # 1 week default

# Features
ALEXANDRIA_ENABLE_REGISTRATION=false          # Allow self-registration
ALEXANDRIA_GUEST_ACCESS=false                 # Allow unauthenticated access

# Auto-admin (Docker/Unraid deployments)
ALEXANDRIA_ADMIN_USERNAME=admin
ALEXANDRIA_ADMIN_PASSWORD=changeme
ALEXANDRIA_ADMIN_EMAIL=admin@example.com
```

### Security Best Practices

1. **Change the secret key** in production:
   ```bash
   # Generate a secure random key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Use strong passwords**:
   - Minimum 8 characters (enforced)
   - Mix of uppercase, lowercase, numbers, symbols recommended

3. **Enable HTTPS** in production:
   - Use a reverse proxy (Traefik, nginx, Caddy)
   - Session cookies will be secure-only

4. **Disable guest access** unless needed

5. **Disable registration** unless you want public signups

## API Endpoints

### Authentication

```bash
# Login
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}

# Response: Sets session cookie, returns user info

# Logout
POST /api/auth/logout

# Get current user
GET /api/auth/me

# Change password
POST /api/auth/change-password
Content-Type: application/json

{
  "current_password": "old-password",
  "new_password": "new-password"
}
```

### Registration (if enabled)

```bash
POST /api/auth/register
Content-Type: application/json

{
  "username": "newuser",
  "password": "secure-password",
  "email": "user@example.com",
  "display_name": "New User"
}
```

## Session Management

### How Sessions Work

- **Cookie-based**: Session ID stored in httpOnly cookie
- **Server-side**: Session data stored in PostgreSQL `sessions` table
- **Secure**:
  - Argon2id password hashing
  - CSRF protection ready
  - Automatic session cleanup
- **Expiration**: Configurable (default: 1 week)
- **IP tracking**: Sessions log IP address and user agent

### Session Cleanup

Old sessions are automatically cleaned up. You can also manually clean expired sessions:

```bash
# Inside container
docker exec alexandria-backend uv run python -c "
from web.database import SessionLocal
from web.auth.session import cleanup_expired_sessions
db = SessionLocal()
deleted = cleanup_expired_sessions(db)
print(f'Deleted {deleted} expired sessions')
db.close()
"
```

## Forward Auth (Advanced)

Alexandria supports forward authentication for integration with reverse proxies like Traefik + Authelia.

```bash
# Enable forward auth
ALEXANDRIA_AUTH_MODE=forward_auth  # or 'both'

# Configure headers
ALEXANDRIA_FORWARD_AUTH_USER_HEADER=X-Forwarded-User
ALEXANDRIA_FORWARD_AUTH_EMAIL_HEADER=X-Forwarded-Email
ALEXANDRIA_FORWARD_AUTH_GROUPS_HEADER=X-Forwarded-Groups
ALEXANDRIA_FORWARD_AUTH_ADMIN_GROUP=admins
```

With forward auth enabled:
- Users are created automatically on first access
- Username comes from the configured header
- Admin status based on group membership

## Troubleshooting

### "No users exist and ALEXANDRIA_ADMIN_USERNAME not set"

You see this warning on startup. Either:
1. Set environment variables for auto-admin creation
2. Create admin manually: `docker exec -it alexandria-backend uv run librarian create-admin`

### "Username already exists"

The admin user already exists. To reset password:
1. Access the database directly
2. Use the change-password endpoint
3. Or create a new admin with a different username

### Session expires too quickly

Increase session expiration:
```bash
ALEXANDRIA_SESSION_EXPIRE_MINUTES=43200  # 30 days
```

### Can't login after container restart

If you're using `ALEXANDRIA_SECRET_KEY`, make sure it's consistent across restarts. Don't use a random value that changes on each startup.

## Multi-User Features

### Collections (Piles)

Each user can create personal collections:
- **To Read** (built-in)
- **Reading** (built-in)
- **Finished** (built-in)
- Custom piles

### Reading Progress

Progress is tracked per-user, per-item:
- Percentage complete
- Last accessed time
- Position/location (for EPUB)
- Syncs with web reader

### Statistics

Each user gets personal reading statistics:
- Books read (month/year/all-time)
- Reading streak
- Favourite authors/genres
- Reading goals (future)

## Database Schema

### users table
```sql
- id: Primary key
- username: Unique username
- email: Optional email (unique)
- password_hash: Argon2id hash
- display_name: Display name
- is_admin: Admin flag
- can_download: Download permission
- created_at: Registration timestamp
- last_login: Last login timestamp
```

### sessions table
```sql
- id: Session token (primary key)
- user_id: Foreign key to users
- ip_address: Client IP
- user_agent: Client user agent
- created_at: Session start
- last_accessed: Last activity
- expires_at: Expiration time
```

## Future Features

Planned authentication enhancements:
- OAuth/OIDC support (Authelia, Authentik, Keycloak)
- API tokens for third-party apps
- Two-factor authentication (TOTP)
- Session management UI (view/revoke sessions)
- Password reset via email
- User invitations
