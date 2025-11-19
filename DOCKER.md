# Docker & Nix Deployment Guide

Complete guide for building and deploying manim-gpt using Docker with Nix package manager.

## Table of Contents

- [Quick Start](#quick-start)
- [Building Docker Images](#building-docker-images)
- [Using Docker Compose](#using-docker-compose)
- [GitHub Actions CI/CD](#github-actions-cicd)
- [Nix Flakes](#nix-flakes)
- [Environment Variables](#environment-variables)
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
  -e OPENAI_API_KEY=your-key-here \
  ghcr.io/YOUR_USERNAME/manim-gpt:latest

# Access the API
curl http://localhost:8000/health
```

### Build and Run Locally

```bash
# Using the build script (easiest)
./build-nix-docker.sh --dockerfile --run

# Or manually
docker build -t manim-gpt:latest .
docker run -d -p 8000:8000 --env-file .env manim-gpt:latest
```

## Building Docker Images

### Option 1: Standard Dockerfile

Uses Nix package manager inside Docker for reproducible builds.

```bash
docker build -f Dockerfile -t manim-gpt:latest .
```

**Advantages:**
- Standard Docker workflow
- Multi-platform support (amd64, arm64)
- Smaller final image size
- Works with docker-compose

### Option 2: Nix-optimized Dockerfile

Optimized build using Nix features.

```bash
docker build -f Dockerfile.nix -t manim-gpt:nix .
```

**Advantages:**
- Faster builds with Nix caching
- Exact dependency reproducibility
- Better layer caching

### Option 3: Pure Nix Build (flake.nix)

Build using Nix flakes for maximum reproducibility.

```bash
# Build the Docker image
nix build .#dockerImage --impure

# Load into Docker
docker load < result

# Tag and run
docker tag manim-gpt:latest manim-gpt:nix
docker run -d -p 8000:8000 manim-gpt:nix
```

**Advantages:**
- Complete reproducibility
- Declarative dependencies
- Works offline (after first build)
- No Docker BuildKit required

### Using the Build Script

The `build-nix-docker.sh` script automates building and running:

```bash
# Make executable
chmod +x build-nix-docker.sh

# Build with standard Dockerfile
./build-nix-docker.sh --dockerfile

# Build with Nix Dockerfile
./build-nix-docker.sh --nix-docker

# Build with Nix flakes
./build-nix-docker.sh --flake

# Build and run immediately
./build-nix-docker.sh --dockerfile --run

# Stop running container
./build-nix-docker.sh --stop
```

## Using Docker Compose

### Start All Services

```bash
# Start backend only
docker-compose up -d manim-gpt-api

# Start backend + Gradio UI
docker-compose up -d manim-gpt-api manim-gpt-gradio

# Start all services (including React frontend)
docker-compose up -d
```

### Configuration

Edit `docker-compose.yml` or create a `.env` file:

```bash
# .env file
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
CEREBRAS_API_KEY=...
```

### Managing Services

```bash
# View logs
docker-compose logs -f manim-gpt-api

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```

## GitHub Actions CI/CD

This project includes comprehensive GitHub Actions workflows for automated building and publishing.

### Workflows

#### 1. **docker-build-push.yml** - Main Docker Build
Triggers on: Push to main/develop, tags, PRs

**Features:**
- Multi-platform builds (amd64, arm64)
- Automatic tagging (latest, version, SHA)
- Publishes to GitHub Container Registry (GHCR)
- Optional Docker Hub publishing
- Build caching for faster builds

#### 2. **docker-nix-build.yml** - Nix-based Build
Triggers on: Push to main/develop, tags

**Features:**
- Pure Nix flake builds
- Cachix integration for Nix cache
- Reproducible builds
- Separate image tags (nix-latest, nix-v1.0.0)

#### 3. **release.yml** - Release Automation
Triggers on: Version tags (v*)

**Features:**
- Creates GitHub releases with changelog
- Builds both standard and Nix images
- Generates SBOM (Software Bill of Materials)
- Multi-platform support
- Updates Docker Hub description

#### 4. **ci.yml** - Continuous Integration
Triggers on: All pushes and PRs

**Features:**
- Linting and formatting checks
- Docker build tests
- Nix flake validation
- Security scanning (Trivy)
- Container health checks

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

3. **Optional: Configure Cachix (for Nix caching):**
   ```bash
   # Create Cachix account and cache
   # Add repository secret:
   CACHIX_AUTH_TOKEN=your-token
   ```

### Using Published Images

```bash
# GitHub Container Registry
docker pull ghcr.io/YOUR_USERNAME/manim-gpt:latest
docker pull ghcr.io/YOUR_USERNAME/manim-gpt:v1.0.0
docker pull ghcr.io/YOUR_USERNAME/manim-gpt:nix-latest

# Docker Hub (if configured)
docker pull YOUR_USERNAME/manim-gpt:latest
```

### Creating a Release

```bash
# Tag a new version
git tag v1.0.0
git push origin v1.0.0

# This automatically:
# 1. Creates a GitHub release
# 2. Builds Docker images
# 3. Publishes to registries
# 4. Generates SBOM
```

## Nix Flakes

### Development Shell

Enter a complete development environment with all dependencies:

```bash
nix develop --impure
```

This provides:
- Python 3.14 + uv
- FFmpeg
- LaTeX (TeX Live)
- Cairo, Pango, and graphics libraries
- Node.js for frontend

### Building with Nix

```bash
# Build the package
nix build .#default --impure

# Build Docker image
nix build .#dockerImage --impure

# Check flake
nix flake check --impure

# Update dependencies
nix flake update
```

### Nix Commands Reference

```bash
# Show flake info
nix flake show

# Show package metadata
nix flake metadata

# Format Nix files
nix fmt

# Run in development shell
nix develop --impure -c uvicorn main:app --reload
```

## Environment Variables

### Required Variables

```bash
# At least one LLM provider API key
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
# OR
CEREBRAS_API_KEY=...
```

### Optional Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Manim Configuration
MANIM_QUALITY=medium  # low, medium, high, 4k
DEFAULT_FORMAT=mp4    # mp4, webm, gif, mov

# LLM Configuration
DEFAULT_MODEL=cerebras/zai-glm-4.6
MAX_ITERATIONS=10
```

### Setting Variables in Docker

```bash
# Method 1: Environment file
docker run --env-file .env manim-gpt:latest

# Method 2: Individual variables
docker run -e OPENAI_API_KEY=sk-... manim-gpt:latest

# Method 3: Docker Compose
# Add to docker-compose.yml under 'environment:'
```

## Advanced Usage

### Multi-stage Caching

Build with layer caching for faster iterations:

```bash
# First build
docker build --cache-from manim-gpt:latest -t manim-gpt:latest .

# Subsequent builds use cache
docker build --cache-from manim-gpt:latest -t manim-gpt:dev .
```

### Build Arguments

```bash
docker build \
  --build-arg VERSION=1.0.0 \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  -t manim-gpt:1.0.0 .
```

### Volume Mounts

```bash
# Persist generated videos
docker run -d \
  -v $(pwd)/media:/app/media \
  -v /tmp/manim_videos:/tmp/manim_videos \
  manim-gpt:latest

# Mount custom code (development)
docker run -d \
  -v $(pwd)/api:/app/api \
  -v $(pwd)/services:/app/services \
  manim-gpt:latest
```

### Resource Limits

```bash
docker run -d \
  --memory=4g \
  --cpus=2 \
  --name manim-gpt \
  manim-gpt:latest
```

## Troubleshooting

### Build Issues

**Problem:** Nix build fails with "experimental features"
```bash
# Solution: Enable flakes
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

**Problem:** Docker build fails on ARM (M1/M2 Mac)
```bash
# Solution: Use multi-platform build
docker buildx build --platform linux/arm64 -t manim-gpt:latest .
```

**Problem:** UV sync fails in container
```bash
# Solution: Clear cache and rebuild
docker build --no-cache -t manim-gpt:latest .
```

### Runtime Issues

**Problem:** Container exits immediately
```bash
# Check logs
docker logs manim-gpt

# Run interactively
docker run -it --entrypoint /bin/bash manim-gpt:latest
```

**Problem:** LaTeX errors
```bash
# The Nix build includes full TeXLive
# If using custom Dockerfile, ensure texlive is installed
```

**Problem:** FFmpeg not found
```bash
# Verify FFmpeg in container
docker exec manim-gpt ffmpeg -version
```

### Performance Issues

**Problem:** Slow video generation
```bash
# Increase resources
docker update --cpus=4 --memory=8g manim-gpt

# Use quality presets
# In .env: MANIM_QUALITY=low
```

**Problem:** Large image size
```bash
# Use Dockerfile.nix for smaller images
# Or use multi-stage builds to reduce layers
```

## Security Best Practices

1. **Never commit API keys** - use environment variables or secrets
2. **Use read-only volumes** where possible
3. **Run container as non-root user** (configured in Dockerfile)
4. **Scan images regularly**:
   ```bash
   docker scan manim-gpt:latest
   ```
5. **Keep base images updated**:
   ```bash
   nix flake update
   docker-compose pull
   ```

## Contributing

When adding new dependencies:

1. Update `pyproject.toml`
2. Update `flake.nix` if system dependencies needed
3. Rebuild Docker image
4. Test all three build methods
5. Update this documentation

## Resources

- [Nix Package Manager](https://nixos.org/)
- [Docker Documentation](https://docs.docker.com/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Nix Flakes](https://nixos.wiki/wiki/Flakes)
- [Manim Documentation](https://docs.manim.community/)
