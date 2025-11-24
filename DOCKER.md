# Docker Deployment Guide

Complete guide for building and deploying manim-gpt using Docker.

## Table of Contents

- [Quick Start](#quick-start)
- [Building Docker Images](#building-docker-images)
- [Running the Container](#running-the-container)
- [GitHub Actions CI/CD](#github-actions-cicd)
- [Environment Variables](#environment-variables)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Pull Pre-built Image (GitHub Container Registry)

```bash
# Pull the latest image
docker pull ghcr.io/YOUR_USERNAME/manim-gpt:latest

# Run the container
docker run -d \
  --name manim-gpt \
  -p 8000:8000 \
  -p 5173:5173 \
  --env-file .env \
  ghcr.io/YOUR_USERNAME/manim-gpt:latest

# Access the services
curl http://localhost:8000/health  # API
open http://localhost:5173          # Frontend UI
```

### Build and Run Locally

```bash
# Build the image
docker build -t manim-gpt:latest .

# Run with environment file
docker run -d \
  -p 8000:8000 \
  -p 5173:5173 \
  --env-file .env \
  --name manim-gpt \
  manim-gpt:latest

# View logs
docker logs -f manim-gpt
```

## Building Docker Images

### Multi-Stage Debian Build

The Dockerfile uses a multi-stage build process for optimal image size and security:

**Stage 1: Builder**
- Full build environment with development headers
- Builds Python packages with C extensions (pycairo, manimpango, moderngl)
- Builds React frontend with Vite
- Installs Node.js 20

**Stage 2: Runtime**
- Minimal runtime environment (debian:bookworm-slim)
- Only runtime libraries (no dev packages)
- TeX Live for LaTeX rendering
- FFmpeg for video processing
- Both backend and frontend included

### Build Command

```bash
# Standard build
docker build -t manim-gpt:latest .

# Build for specific platform
docker build --platform linux/amd64 -t manim-gpt:latest .
docker build --platform linux/arm64 -t manim-gpt:latest .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t manim-gpt:latest .

# Build with no cache
docker build --no-cache -t manim-gpt:latest .
```

### Image Details

**Included Components:**
- Python 3.11 with all dependencies
- Node.js 20 for frontend
- TeX Live (latex-base, latex-extra, fonts, science packages)
- FFmpeg for video processing
- Ghostscript for PostScript/PDF
- All graphics libraries (Cairo, Pango, Harfbuzz, Fontconfig, Freetype)
- React frontend (Vite + Tailwind CSS)
- FastAPI backend

**Services:**
- FastAPI backend on port 8000
- React frontend on port 5173
- Both services start automatically via startup script

## Running the Container

### Basic Run

```bash
docker run -d \
  --name manim-gpt \
  -p 8000:8000 \
  -p 5173:5173 \
  --env-file .env \
  manim-gpt:latest
```

### With Specific API Keys

```bash
docker run -d \
  --name manim-gpt \
  -p 8000:8000 \
  -p 5173:5173 \
  -e OPENAI_API_KEY=sk-... \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e CEREBRAS_API_KEY=... \
  manim-gpt:latest
```

### With Volume Mounts

```bash
# Persist generated videos
docker run -d \
  --name manim-gpt \
  -p 8000:8000 \
  -p 5173:5173 \
  -v $(pwd)/media:/app/media \
  -v /tmp/manim_videos:/tmp/manim_videos \
  --env-file .env \
  manim-gpt:latest
```

### Container Management

```bash
# View logs
docker logs manim-gpt
docker logs -f manim-gpt  # Follow logs

# Stop container
docker stop manim-gpt

# Start container
docker start manim-gpt

# Restart container
docker restart manim-gpt

# Remove container
docker rm manim-gpt

# Execute command in running container
docker exec -it manim-gpt bash
```

## GitHub Actions CI/CD

### Automated Builds

The project includes GitHub Actions workflow for automated Docker builds:

**Workflow: `docker-build-push.yml`**
- Triggers on: Push to main/develop, tags (v*), PRs
- Multi-platform builds: linux/amd64, linux/arm64
- Automatic tagging: latest, version, SHA
- Publishes to GitHub Container Registry (GHCR)
- Optional Docker Hub publishing
- Build caching for faster builds

### Setup GitHub Actions

1. **Enable GitHub Container Registry:**
   - Go to repo Settings → Actions → General
   - Enable "Read and write permissions" for GITHUB_TOKEN

2. **Optional: Configure Docker Hub:**
   ```bash
   # Add repository secrets:
   DOCKERHUB_USERNAME=your-username
   DOCKERHUB_TOKEN=your-access-token
   ```

### Using Published Images

```bash
# GitHub Container Registry
docker pull ghcr.io/YOUR_USERNAME/manim-gpt:latest
docker pull ghcr.io/YOUR_USERNAME/manim-gpt:v1.0.0

# Docker Hub (if configured)
docker pull YOUR_USERNAME/manim-gpt:latest
```

### Creating a Release

```bash
# Tag a new version
git tag v1.0.0
git push origin v1.0.0

# This automatically:
# 1. Builds Docker image for amd64 and arm64
# 2. Creates a GitHub release
# 3. Publishes to container registries
# 4. Tags with version and latest
```

## Environment Variables

### Required Variables

At least one LLM provider API key is required:

```bash
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
# OR
CEREBRAS_API_KEY=...
# OR
GOOGLE_API_KEY=...
```

### Optional Variables

```bash
# Logging
LITELLM_LOG=INFO
LITELLM_LOG_LEVEL=INFO

# API Configuration
HOST=0.0.0.0
PORT=8000

# Manim Configuration
MANIM_QUALITY=medium  # low, medium, high, 4k
DEFAULT_FORMAT=mp4    # mp4, webm, gif, mov

# LLM Configuration
DEFAULT_MODEL=cerebras/llama-3.3-70b
MAX_ITERATIONS=10
```

### Setting Variables

```bash
# Method 1: Environment file
docker run --env-file .env manim-gpt:latest

# Method 2: Individual variables
docker run \
  -e OPENAI_API_KEY=sk-... \
  -e LITELLM_LOG=INFO \
  manim-gpt:latest

# Method 3: From host environment
docker run --env OPENAI_API_KEY manim-gpt:latest
```

## Advanced Usage

### Resource Limits

```bash
docker run -d \
  --name manim-gpt \
  --memory=4g \
  --cpus=2 \
  -p 8000:8000 \
  -p 5173:5173 \
  manim-gpt:latest
```

### Network Configuration

```bash
# Create custom network
docker network create manim-network

# Run container on custom network
docker run -d \
  --name manim-gpt \
  --network manim-network \
  -p 8000:8000 \
  -p 5173:5173 \
  manim-gpt:latest
```

### Health Checks

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' manim-gpt

# Manual health check
curl http://localhost:8000/health
```

### Build with Cache

```bash
# Use GitHub Actions cache
docker build \
  --cache-from ghcr.io/YOUR_USERNAME/manim-gpt:latest \
  -t manim-gpt:latest .
```

## Troubleshooting

### Build Issues

**Problem:** Build fails during Python package installation
```bash
# Solution: Clean build without cache
docker build --no-cache -t manim-gpt:latest .
```

**Problem:** Build fails on ARM (M1/M2 Mac)
```bash
# Solution: Specify platform
docker build --platform linux/arm64 -t manim-gpt:latest .
```

**Problem:** Frontend build fails
```bash
# Solution: Check Node.js installation in builder stage
docker build --target builder -t test .
docker run -it test node --version
```

### Runtime Issues

**Problem:** Container exits immediately
```bash
# Check logs
docker logs manim-gpt

# Run interactively
docker run -it --entrypoint /bin/bash manim-gpt:latest
```

**Problem:** Frontend not accessible
```bash
# Check if both services are running
docker exec manim-gpt ps aux

# Check frontend logs
docker logs manim-gpt 2>&1 | grep -i vite
```

**Problem:** Backend API errors
```bash
# Check API logs
docker logs manim-gpt 2>&1 | grep -i uvicorn

# Test API directly
curl http://localhost:8000/health
```

**Problem:** LaTeX errors
```bash
# TeX Live is included in the image
# Verify installation:
docker exec manim-gpt latex --version
```

**Problem:** FFmpeg not found
```bash
# Verify FFmpeg installation
docker exec manim-gpt ffmpeg -version
```

### Performance Issues

**Problem:** Slow video generation
```bash
# Increase resources
docker update --cpus=4 --memory=8g manim-gpt

# Use lower quality settings
# Set MANIM_QUALITY=low in environment
```

**Problem:** Large image size (7.66GB)
```bash
# The image includes:
# - Full TeX Live distribution (~2GB)
# - Node.js and npm packages
# - All graphics libraries
# - Python packages with C extensions
#
# This is expected for a complete Manim environment
# To reduce size, consider:
# - Removing TeX Live docs/sources (already done)
# - Using production build of frontend
# - Removing unused packages
```

## Security Best Practices

1. **Never commit API keys** - use environment variables or secrets
2. **Use read-only volumes** where possible
3. **Run with resource limits** to prevent resource exhaustion
4. **Keep images updated**:
   ```bash
   docker pull ghcr.io/YOUR_USERNAME/manim-gpt:latest
   ```
5. **Scan images for vulnerabilities**:
   ```bash
   docker scan manim-gpt:latest
   ```

## Image Architecture

### Multi-Stage Build Benefits

- **Smaller final image**: Build tools and dev headers are not included in runtime
- **Security**: Reduced attack surface with minimal runtime dependencies
- **Performance**: Optimized layers with proper caching
- **Maintainability**: Clear separation between build and runtime environments

### Layer Optimization

The Dockerfile is optimized for layer caching:
1. System dependencies installed first (rarely change)
2. Python dependencies next (change occasionally)
3. Application code last (changes frequently)
4. Frontend built separately with its own caching

This ensures fast rebuilds during development.

## Resources

- [Docker Documentation](https://docs.docker.com/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Manim Documentation](https://docs.manim.community/)

## Contributing

When adding new dependencies:

1. Update `pyproject.toml` for Python packages
2. Update `frontend/package.json` for npm packages
3. Add system dependencies to Dockerfile if needed
4. Test the build locally
5. Update this documentation
