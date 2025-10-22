#!/bin/bash

# Health check script for Polymarket Insider
# This script monitors the health of the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="polymarket-insider"
LOG_FILE="logs/health-check.log"
MAX_LOG_SIZE=10485760  # 10MB

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

# Function to log messages
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Rotate log if it's too large
    if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
    fi

    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Check if container is running
check_container_running() {
    if docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"; then
        print_status "Container $CONTAINER_NAME is running"
        log_message "INFO" "Container $CONTAINER_NAME is running"
        return 0
    else
        print_error "Container $CONTAINER_NAME is not running"
        log_message "ERROR" "Container $CONTAINER_NAME is not running"
        return 1
    fi
}

# Check container health status
check_container_health() {
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")

    case "$health_status" in
        "healthy")
            print_status "Container health status: healthy"
            log_message "INFO" "Container health status: healthy"
            return 0
            ;;
        "unhealthy")
            print_error "Container health status: unhealthy"
            log_message "ERROR" "Container health status: unhealthy"
            return 1
            ;;
        "starting")
            print_warning "Container health status: starting"
            log_message "WARNING" "Container health status: starting"
            return 0
            ;;
        "none"|"unknown")
            print_warning "Container health status: unknown (no health check)"
            log_message "WARNING" "Container health status: unknown"
            return 0
            ;;
    esac
}

# Check recent logs for errors
check_recent_logs() {
    # Get logs from the last 10 minutes
    local error_count=$(docker logs "$CONTAINER_NAME" --since=10m 2>&1 | grep -i "error\|exception\|traceback" | wc -l || echo 0)

    if [ "$error_count" -gt 0 ]; then
        print_warning "Found $error_count errors in recent logs"
        log_message "WARNING" "Found $error_count errors in recent logs"
        return 1
    else
        print_status "No errors found in recent logs"
        log_message "INFO" "No errors found in recent logs"
        return 0
    fi
}

# Check memory usage
check_memory_usage() {
    local memory_usage=$(docker stats --no-stream --format "table {{.MemUsage}}" "$CONTAINER_NAME" | tail -n 1 | cut -d'/' -f1)
    local memory_percentage=$(docker stats --no-stream --format "table {{.MemPerc}}" "$CONTAINER_NAME" | tail -n 1 | tr -d '%')

    # Check if memory usage is above 80%
    if (( $(echo "$memory_percentage > 80" | bc -l) )); then
        print_warning "High memory usage: $memory_percentage% ($memory_usage)"
        log_message "WARNING" "High memory usage: $memory_percentage% ($memory_usage)"
        return 1
    else
        print_status "Memory usage is normal: $memory_percentage% ($memory_usage)"
        log_message "INFO" "Memory usage is normal: $memory_percentage% ($memory_usage)"
        return 0
    fi
}

# Check if the application is responsive
check_application_responsive() {
    # This is a basic check - you might want to implement a more specific health check
    # For example, checking if the WebSocket connection is active
    local process_count=$(docker exec "$CONTAINER_NAME" pgrep -f "polymarket_insider" | wc -l || echo 0)

    if [ "$process_count" -gt 0 ]; then
        print_status "Application process is running ($process_count processes)"
        log_message "INFO" "Application process is running ($process_count processes)"
        return 0
    else
        print_error "Application process is not running"
        log_message "ERROR" "Application process is not running"
        return 1
    fi
}

# Restart container if needed
restart_container() {
    print_warning "Restarting container..."
    log_message "WARNING" "Restarting container due to health check failure"

    docker-compose restart

    print_status "Container restarted"
    log_message "INFO" "Container restarted successfully"
}

# Main health check function
main() {
    local exit_code=0

    print_status "Starting health check for $CONTAINER_NAME"

    # Create logs directory if it doesn't exist
    mkdir -p logs

    # Run all health checks
    if ! check_container_running; then
        exit_code=1
    fi

    if ! check_container_health; then
        exit_code=1
    fi

    if ! check_recent_logs; then
        exit_code=1
    fi

    if ! check_memory_usage; then
        exit_code=1
    fi

    if ! check_application_responsive; then
        exit_code=1
    fi

    # If any check failed, attempt to restart the container
    if [ $exit_code -eq 1 ] && [ "${1:-auto}" = "auto" ]; then
        restart_container
        exit_code=0  # Don't fail the script if we attempted to restart
    fi

    if [ $exit_code -eq 0 ]; then
        print_status "Health check completed successfully"
    else
        print_error "Health check completed with errors"
    fi

    exit $exit_code
}

# Run main function with all arguments
main "$@"