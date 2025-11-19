#!/usr/bin/env bash
# Build script for creating Docker image with Nix

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_msg() {
    echo -e "${2:-$GREEN}$1${NC}"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

print_info() {
    echo -e "${BLUE}INFO: $1${NC}"
}

# Check if Nix is installed
check_nix() {
    if ! command -v nix &> /dev/null; then
        print_error "Nix is not installed!"
        print_info "Install Nix with:"
        echo "  curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install"
        exit 1
    fi
    print_msg "✓ Nix is installed" "$GREEN"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        print_info "Install Docker from https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_msg "✓ Docker is installed" "$GREEN"
}

# Build using flake.nix (recommended)
build_with_flake() {
    print_msg "Building Docker image using Nix flakes..." "$BLUE"

    if [ ! -f "flake.nix" ]; then
        print_error "flake.nix not found!"
        exit 1
    fi

    # Build the Docker image using Nix
    print_info "Building image (this may take a while on first run)..."
    nix build .#dockerImage --impure

    # Load the image into Docker
    print_info "Loading image into Docker..."
    docker load < result

    print_msg "✓ Docker image built successfully!" "$GREEN"
    print_info "Image name: manim-gpt:latest"
}

# Build using Dockerfile with Nix
build_with_dockerfile() {
    print_msg "Building Docker image using Dockerfile with Nix..." "$BLUE"

    local dockerfile="${1:-Dockerfile}"

    if [ ! -f "$dockerfile" ]; then
        print_error "$dockerfile not found!"
        exit 1
    fi

    print_info "Building with $dockerfile..."
    docker build -f "$dockerfile" -t manim-gpt:latest .

    print_msg "✓ Docker image built successfully!" "$GREEN"
}

# Run the Docker container
run_container() {
    print_msg "Starting manim-gpt container..." "$BLUE"

    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_warning ".env file not found, copying from .env.example"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_info "Please edit .env and add your API keys"
        fi
    fi

    # Stop existing container if running
    if docker ps -a | grep -q manim-gpt; then
        print_info "Stopping existing container..."
        docker stop manim-gpt 2>/dev/null || true
        docker rm manim-gpt 2>/dev/null || true
    fi

    # Run the container
    docker run -d \
        --name manim-gpt \
        -p 8000:8000 \
        -p 7860:7860 \
        --env-file .env \
        -v "$(pwd)/media:/app/media" \
        -v "/tmp/manim_videos:/tmp/manim_videos" \
        --restart unless-stopped \
        manim-gpt:latest

    print_msg "✓ Container started successfully!" "$GREEN"
    print_info "API available at: http://localhost:8000"
    print_info "Docs available at: http://localhost:8000/docs"
    print_info "Gradio UI at: http://localhost:7860"
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build and run manim-gpt Docker container with Nix

OPTIONS:
    -f, --flake         Build using flake.nix (recommended)
    -d, --dockerfile    Build using Dockerfile (default)
    -n, --nix-docker    Build using Dockerfile.nix
    -r, --run           Run container after building
    -s, --stop          Stop and remove running container
    -h, --help          Show this help message

EXAMPLES:
    $0 --flake --run           Build with flake and run
    $0 --dockerfile --run      Build with Dockerfile and run
    $0 --stop                  Stop running container

EOF
}

# Main
main() {
    local build_method="dockerfile"
    local should_run=false
    local should_stop=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--flake)
                build_method="flake"
                shift
                ;;
            -d|--dockerfile)
                build_method="dockerfile"
                shift
                ;;
            -n|--nix-docker)
                build_method="nix-dockerfile"
                shift
                ;;
            -r|--run)
                should_run=true
                shift
                ;;
            -s|--stop)
                should_stop=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    print_msg "=== Manim GPT Docker Build Script ===" "$BLUE"
    echo

    # Stop container if requested
    if [ "$should_stop" = true ]; then
        print_info "Stopping container..."
        docker stop manim-gpt 2>/dev/null || true
        docker rm manim-gpt 2>/dev/null || true
        print_msg "✓ Container stopped" "$GREEN"
        exit 0
    fi

    # Check prerequisites
    check_docker

    # Build based on method
    case $build_method in
        flake)
            check_nix
            build_with_flake
            ;;
        dockerfile)
            build_with_dockerfile "Dockerfile"
            ;;
        nix-dockerfile)
            check_nix
            build_with_dockerfile "Dockerfile.nix"
            ;;
    esac

    # Run container if requested
    if [ "$should_run" = true ]; then
        run_container
    else
        print_info "To run the container, use: $0 --run"
        print_info "Or use docker-compose: docker-compose up -d"
    fi

    echo
    print_msg "=== Build Complete ===" "$GREEN"
}

# Run main function
main "$@"
