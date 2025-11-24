# Optimized multi-stage Dockerfile for manim-gpt using Debian
# Migrated from NixOS to reduce image size and improve compatibility
# Expected final size: ~1.3GB (vs ~2.5-3.5GB with NixOS)

# ============================================================================
# Stage 1: Builder - Has all build tools and dev headers
# ============================================================================
FROM debian:bookworm AS builder

# Install build dependencies and dev headers
RUN apt-get update && apt-get install -y \
    # Core build tools
    build-essential \
    gcc \
    g++ \
    make \
    pkg-config \
    meson \
    ninja-build \
    # Python development (Debian Bookworm has Python 3.11)
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    # Graphics library development headers
    libcairo2-dev \
    libpango1.0-dev \
    libglib2.0-dev \
    libharfbuzz-dev \
    libfontconfig1-dev \
    libfreetype-dev \
    libpixman-1-dev \
    libpng-dev \
    # X11 development headers
    libxcb1-dev \
    libx11-dev \
    x11proto-dev \
    libxcb-render0-dev \
    libxcb-shm0-dev \
    # Utilities
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set build environment variables
ENV PKG_CONFIG_PATH=/usr/lib/x86_64-linux-gnu/pkgconfig \
    PYTHONUNBUFFERED=1

# Set up app directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Build Python dependencies with C extensions
RUN uv venv && \
    . .venv/bin/activate && \
    uv sync --frozen

# Install Node.js 20 for frontend build
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy application code (after deps to leverage caching)
COPY api ./api
COPY models ./models
COPY services ./services
COPY utils ./utils
COPY main.py ./

# Copy and build frontend
COPY frontend ./frontend
WORKDIR /app/frontend
RUN npm install && npm run build
WORKDIR /app

# ============================================================================
# Stage 2: Runtime - Minimal runtime dependencies only
# ============================================================================
FROM debian:bookworm-slim

# Install ONLY runtime dependencies (no build tools or -dev packages)
RUN apt-get update && apt-get install -y \
    # Shell and process management
    bash \
    procps \
    # Python runtime (Debian Bookworm has Python 3.11)
    python3 \
    python3-pip \
    # Graphics runtime libraries (no -dev)
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libglib2.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libfreetype6 \
    libpixman-1-0 \
    libpng16-16 \
    # X11 runtime libraries
    libxcb1 \
    libx11-6 \
    libxcb-render0 \
    libxcb-shm0 \
    # Media processing
    ffmpeg \
    # Document processing
    ghostscript \
    # TeX Live for LaTeX rendering
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-science \
    dvisvgm \
    # Utilities
    curl \
    ca-certificates \
    # Fonts for Manim
    fonts-liberation \
    fonts-dejavu-core \
    gsfonts \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Node.js 20 (for frontend if needed)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy uv from builder stage (avoids needing build tools in runtime)
COPY --from=builder /root/.local/bin/uv /usr/local/bin/uv
COPY --from=builder /root/.local/bin/uvx /usr/local/bin/uvx

# Optimize TeX Live size by removing docs and sources
RUN rm -rf /usr/share/texlive/texmf-dist/doc \
    && rm -rf /usr/share/texlive/texmf-dist/source

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/app/.venv/bin:$PATH" \
    LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu

# Set up app directory
WORKDIR /app

# Copy .env.example
COPY .env.example ./.env.example

# Copy application and virtual environment from builder
COPY --from=builder /app ./

# Create startup script to run both backend and frontend
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'set -e' >> /app/start.sh && \
    echo 'echo "Starting Manim GPT services..."' >> /app/start.sh && \
    echo 'cd /app/frontend && npm run dev -- --host 0.0.0.0 --port 5173 &' >> /app/start.sh && \
    echo 'FRONTEND_PID=$!' >> /app/start.sh && \
    echo 'cd /app && uv run uvicorn main:app --host 0.0.0.0 --port 8000 &' >> /app/start.sh && \
    echo 'BACKEND_PID=$!' >> /app/start.sh && \
    echo 'echo "Frontend running on port 5173 (PID: $FRONTEND_PID)"' >> /app/start.sh && \
    echo 'echo "Backend running on port 8000 (PID: $BACKEND_PID)"' >> /app/start.sh && \
    echo 'wait' >> /app/start.sh && \
    chmod +x /app/start.sh

# Clean up Python cache files to reduce size
RUN find /app/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type f -name "*.pyc" -delete 2>/dev/null || true

# Create directory for temporary video files
RUN mkdir -p /tmp/manim_videos && chmod 777 /tmp/manim_videos

# Expose ports
EXPOSE 8000 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run both backend and frontend
CMD ["/bin/bash", "/app/start.sh"]
