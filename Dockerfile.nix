# Optimized Dockerfile using Nix for manim-gpt
# This provides a smaller, more efficient image

FROM nixos/nix:2.18.1 AS builder

# Enable Nix flakes and commands
RUN mkdir -p /etc/nix && \
    echo "experimental-features = nix-command flakes" >> /etc/nix/nix.conf && \
    echo "sandbox = false" >> /etc/nix/nix.conf

WORKDIR /build

# Copy flake files first for better caching
COPY flake.nix flake.lock* ./

# Build the Nix package
RUN nix build .#dockerImage --impure --no-link

# Alternative: Use nix develop to install dependencies
COPY . .
RUN nix develop --impure -c bash -c "uv sync"

# Final stage: Minimal runtime image
FROM nixos/nix:2.18.1

# Enable Nix features
RUN mkdir -p /etc/nix && \
    echo "experimental-features = nix-command flakes" >> /etc/nix/nix.conf

# Install runtime dependencies via Nix
RUN nix-env -iA nixpkgs.python314 \
                 nixpkgs.uv \
                 nixpkgs.cairo \
                 nixpkgs.pango \
                 nixpkgs.ffmpeg \
                 nixpkgs.texlive.combined.scheme-medium \
                 nixpkgs.ghostscript \
                 nixpkgs.curl \
                 nixpkgs.bash

# Set working directory
WORKDIR /app

# Copy application code
COPY --from=builder /build .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/app/.venv/bin:/root/.nix-profile/bin:$PATH"

# Create necessary directories
RUN mkdir -p /tmp/manim_videos && chmod 777 /tmp/manim_videos

# Expose ports
EXPOSE 8000 7860 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
