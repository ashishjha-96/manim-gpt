# Multi-stage Dockerfile using Nix for manim-gpt
# This creates a reproducible build environment with all dependencies

# Stage 1: Nix builder stage
FROM nixos/nix:latest AS builder

# Enable flakes and nix-command (experimental features)
RUN echo "experimental-features = nix-command flakes" >> /etc/nix/nix.conf

# Copy the Nix configuration
WORKDIR /build
COPY .idx/dev.nix .

# Create a shell.nix that uses the dev.nix configuration
RUN echo '{ pkgs ? import <nixpkgs> {} }:' > shell.nix && \
    echo 'let' >> shell.nix && \
    echo '  devEnv = import ./dev.nix { inherit pkgs; };' >> shell.nix && \
    echo 'in' >> shell.nix && \
    echo 'pkgs.mkShell {' >> shell.nix && \
    echo '  buildInputs = devEnv.packages;' >> shell.nix && \
    echo '  shellHook = '"'"'' >> shell.nix && \
    echo '    ${builtins.concatStringsSep "\n" (pkgs.lib.mapAttrsToList (name: value: "export ${name}=\"${value}\"") devEnv.env)}' >> shell.nix && \
    echo '  '"'"';' >> shell.nix && \
    echo '}' >> shell.nix

# Build the Nix environment and export it
RUN nix-shell shell.nix --run "echo 'Nix environment built successfully'"

# Stage 2: Runtime stage
FROM nixos/nix:latest

# Enable flakes and nix-command
RUN echo "experimental-features = nix-command flakes" >> /etc/nix/nix.conf

# Install necessary system packages
RUN nix-env -iA \
    nixpkgs.python314 \
    nixpkgs.uv \
    nixpkgs.gcc \
    nixpkgs.cairo \
    nixpkgs.pkg-config \
    nixpkgs.ffmpeg \
    nixpkgs.pango \
    nixpkgs.glib \
    nixpkgs.harfbuzz \
    nixpkgs.fontconfig \
    nixpkgs.freetype \
    nixpkgs.ghostscript \
    nixpkgs.nodejs_20

# Install TeX Live for Manim
RUN nix-env -iA nixpkgs.texlive.combined.scheme-medium

# Set environment variables for building Python packages
ENV PKG_CONFIG_PATH=/nix/var/nix/profiles/default/lib/pkgconfig
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# Create app directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY .env.example ./.env.example

# Copy application code
COPY api ./api
COPY models ./models
COPY services ./services
COPY utils ./utils
COPY main.py ./
COPY gradio_app.py ./

# Copy frontend (optional, for React UI)
COPY frontend ./frontend

# Install Python dependencies using uv
RUN uv sync --frozen

# Create directory for temporary video files
RUN mkdir -p /tmp/manim_videos && chmod 777 /tmp/manim_videos

# Expose ports
# 8000 for FastAPI backend
# 7860 for Gradio UI
# 5173 for React frontend (if needed)
EXPOSE 8000 7860 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run the FastAPI backend
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
