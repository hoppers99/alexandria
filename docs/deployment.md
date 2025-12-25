# Deployment Guide

This guide covers deploying Alexandria to production environments.

## Docker Images

Pre-built Docker images are published to GitHub Container Registry (GHCR) on each release:

- `ghcr.io/<owner>/<repo>-backend:latest` - Python backend API
- `ghcr.io/<owner>/<repo>-frontend:latest` - SvelteKit frontend

Images are tagged with:
- `latest` - most recent release
- `vX.Y.Z` - specific version (e.g., `v0.1.0`)
- `vX.Y` - minor version (e.g., `v0.1`)

## Production Deployment

### Using Docker Compose

1. Download the production compose file:
   ```bash
   curl -O https://raw.githubusercontent.com/<owner>/<repo>/main/docker-compose.prod.yml
   ```

2. Create an environment file:
   ```bash
   cat > .env << EOF
   ALEXANDRIA_LIBRARY_ROOT=/path/to/your/library
   ALEXANDRIA_DB_PASSWORD=change-me-in-production
   EOF
   ```

3. Start the services:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. Run database migrations:
   ```bash
   docker-compose -f docker-compose.prod.yml exec backend uv run alembic upgrade head
   ```

5. Seed classification data:
   ```bash
   docker-compose -f docker-compose.prod.yml exec backend uv run librarian seed
   ```

6. Access the web UI at http://localhost:3000

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALEXANDRIA_LIBRARY_ROOT` | Path to your library folder (required) | - |
| `ALEXANDRIA_DB_PASSWORD` | PostgreSQL password | `alexandria` |
| `ALEXANDRIA_CONFIDENCE_THRESHOLD` | Auto-file confidence threshold (0.0-1.0) | `0.8` |

### Unraid

Alexandria can be installed on Unraid via Docker Compose:

1. Install the **Docker Compose Manager** plugin from Community Apps
2. Create a new stack and paste the contents of `docker-compose.prod.yml`
3. Configure paths and environment variables for your setup
4. Start the stack

### Reverse Proxy

For production deployments behind a reverse proxy (nginx, Traefik, Caddy), ensure:

1. The `ORIGIN` environment variable on the frontend matches your public URL
2. WebSocket connections are proxied correctly (for hot reload in dev)
3. The `/api` path is accessible through the proxy

Example nginx configuration:
```nginx
server {
    listen 80;
    server_name library.example.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Building Images Locally

To build images locally instead of using GHCR:

```bash
# Clone the repository
git clone https://github.com/<owner>/<repo>.git
cd <repo>

# Build backend
docker build -t alexandria-backend .

# Build frontend
docker build -t alexandria-frontend ./frontend
```

## CI/CD Pipeline

The repository includes a GitHub Actions workflow (`.github/workflows/docker-publish.yml`) that automatically builds and publishes Docker images.

### Automatic Releases

Images are built and pushed when:
- A version tag is pushed (e.g., `git tag v0.1.0 && git push origin v0.1.0`)

### Manual Builds

Images can also be built manually:
1. Go to Actions → "Build and Publish Docker Images"
2. Click "Run workflow"
3. Optionally specify a custom tag (defaults to `dev`)

### Setting Up CI/CD for Your Fork

If you fork this repository, the GitHub Actions workflow will work automatically because it uses `GITHUB_TOKEN` for authentication. No additional secrets are required.

The workflow:
1. Builds both backend and frontend images in parallel
2. Pushes to `ghcr.io/<your-username>/<repo>-backend` and `ghcr.io/<your-username>/<repo>-frontend`
3. Uses GitHub's build cache for faster subsequent builds

To enable the workflow:
1. Go to your fork's Settings → Actions → General
2. Under "Workflow permissions", select "Read and write permissions"
3. Push a version tag to trigger the first build
