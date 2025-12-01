# Reusable builder base image for manim-gpt
# Contains all system packages and build tools needed for compiling dependencies
# Push to Docker Hub: ajha2025/manim-gpt:builder-*
# Rebuild monthly or when system dependencies change

FROM debian:bookworm AS manim-builder-base

# Install ALL system packages needed for building
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
    # Graphics library development headers (for pycairo, manimpango, moderngl)
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

# Install Node.js 20 LTS for frontend builds
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Install uv package manager (faster than pip)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set build environment variables
# Reduce optimization to prevent QEMU segfaults during cross-compilation
ENV PKG_CONFIG_PATH=/usr/lib/x86_64-linux-gnu/pkgconfig \
    PYTHONUNBUFFERED=1 \
    CFLAGS="-O1" \
    CXXFLAGS="-O1"

WORKDIR /build

# Image metadata
LABEL maintainer="Ashish Jha"
LABEL description="Builder base image for manim-gpt with all build dependencies"
LABEL version="1.0.0"
