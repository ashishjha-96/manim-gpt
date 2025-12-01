# Optimized multi-stage Dockerfile for manim-gpt
# Uses reusable builder image for faster builds
# Expected final size: ~5GB (vs ~7.66GB with previous version)

# ============================================================================
# Stage 1: Python Dependencies Builder
# ============================================================================
FROM ajha2025/manim-gpt:builder-latest AS python-builder

WORKDIR /build

# Copy ONLY dependency files first (better caching)
# This layer only rebuilds when dependencies change
COPY pyproject.toml uv.lock ./

# Build Python virtual environment with all dependencies
# Reduce compiler optimization to avoid QEMU segfaults when cross-compiling
ENV CFLAGS="-O1" \
    CXXFLAGS="-O1"

RUN uv venv /build/.venv && \
    . /build/.venv/bin/activate && \
    uv sync --frozen

# Optimize venv size - remove cache files
RUN find /build/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /build/.venv -type f -name "*.pyc" -delete 2>/dev/null || true && \
    find /build/.venv -type f -name "*.pyo" -delete 2>/dev/null || true

# ============================================================================
# Stage 2: Frontend Builder
# ============================================================================
FROM ajha2025/manim-gpt:builder-latest AS frontend-builder

WORKDIR /build/frontend

# Copy ONLY package files first (better caching)
# This layer only rebuilds when frontend dependencies change
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies with npm ci (faster and more reliable than npm install)
RUN npm ci

# Copy source code AFTER deps installed
COPY frontend/ ./

# Build production static files to dist/
# Vite will create dist/ with index.html and assets/ directory
RUN npm run build

# Verify build output exists
RUN ls -lah dist/ && \
    echo "Frontend build completed successfully" && \
    du -sh dist/

# ============================================================================
# Stage 3: Runtime - Uses runtime base image with all dependencies pre-installed
# ============================================================================
FROM ajha2025/manim-gpt:runtime-latest AS runtime

# Copy uv binaries from builder (avoids needing build tools in runtime)
COPY --from=ajha2025/manim-gpt:builder-latest /root/.local/bin/uv /usr/local/bin/uv
COPY --from=ajha2025/manim-gpt:builder-latest /root/.local/bin/uvx /usr/local/bin/uvx

# Set additional environment variables (base ones are in runtime image)
ENV UV_SYSTEM_PYTHON=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy Python virtual environment from builder
COPY --from=python-builder /build/.venv /app/.venv

# Fix shebangs in venv scripts (they point to /build instead of /app)
RUN find /app/.venv/bin -type f -exec sed -i 's|#!/build/.venv|#!/app/.venv|g' {} \;

# Copy application code
COPY api ./api
COPY models ./models
COPY services ./services
COPY utils ./utils
COPY main.py ./

# Copy ONLY built frontend static files (not node_modules!)
# This is the production build from Vite
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Create directory for temporary video files
RUN mkdir -p /tmp/manim_videos && chmod 777 /tmp/manim_videos

# Expose port 8000 for both API and frontend
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run ONLY FastAPI (serves both API and static frontend)
# No need for npm dev server anymore
# Use python -m uvicorn since shebangs point to /build path
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
