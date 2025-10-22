#!/bin/bash

# Polymarket Insider Deployment Script
# This script handles deployment to different environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    print_status "Docker and Docker Compose are installed"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_warning ".env file not found. Copying from .env.example"
        cp .env.example .env
        print_warning "Please edit .env file with your configuration before running the application"
        exit 1
    fi

    print_status ".env file found"
}

# Build and deploy with Docker
deploy_docker() {
    print_status "Building Docker image..."
    docker-compose build

    print_status "Starting application with Docker Compose..."
    docker-compose up -d

    print_status "Application is running in the background"
    print_status "Check logs with: docker-compose logs -f polymarket-insider"
    print_status "Stop with: docker-compose down"
}

# Local development deployment
deploy_local() {
    print_status "Setting up local development environment..."

    # Check if UV is installed
    if ! command -v uv &> /dev/null; then
        print_error "UV is not installed. Please install UV first."
        exit 1
    fi

    print_status "Installing dependencies with UV..."
    uv sync

    print_status "Starting application in development mode..."
    uv run python -m polymarket_insider
}

# Main deployment function
main() {
    print_status "Starting Polymarket Insider deployment..."

    check_docker

    # Parse command line arguments
    case "${1:-docker}" in
        "docker")
            check_env_file
            deploy_docker
            ;;
        "local")
            check_env_file
            deploy_local
            ;;
        "update")
            print_status "Updating Docker container..."
            docker-compose down
            docker-compose build --no-cache
            docker-compose up -d
            ;;
        "stop")
            print_status "Stopping application..."
            docker-compose down
            ;;
        "logs")
            docker-compose logs -f polymarket-insider
            ;;
        "status")
            docker-compose ps
            ;;
        *)
            echo "Usage: $0 {docker|local|update|stop|logs|status}"
            echo ""
            echo "Commands:"
            echo "  docker  - Deploy with Docker (recommended for production)"
            echo "  local   - Deploy locally for development"
            echo "  update  - Update and restart Docker container"
            echo "  stop    - Stop the application"
            echo "  logs    - Show application logs"
            echo "  status  - Show container status"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"