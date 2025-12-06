#!/bin/bash
# Database Migration Helper Script
# Run this to create and apply database migrations

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== SomniProperty Database Migration Tool ===${NC}"
echo

# Check if we're in the right directory
if [ ! -f "alembic.ini" ]; then
    echo -e "${RED}Error: alembic.ini not found. Run this from the backend directory.${NC}"
    exit 1
fi

# Function to run migrations
run_migration() {
    local command=$1
    local message=$2

    echo -e "${GREEN}${message}${NC}"

    # Check if we're in Kubernetes or local
    if kubectl get pods -n somniproperty -l component=backend &> /dev/null; then
        echo "Running in Kubernetes pod..."
        POD=$(kubectl get pods -n somniproperty -l component=backend -o jsonpath='{.items[0].metadata.name}')
        kubectl exec -n somniproperty $POD -- $command
    else
        echo "Running locally..."
        eval $command
    fi
}

# Parse command line arguments
case "${1:-help}" in
    init)
        echo "Generating initial migration from models..."
        run_migration "alembic revision --autogenerate -m 'Initial schema with 14 tables'" \
                      "Creating initial migration..."
        echo
        echo -e "${GREEN}✅ Migration file created in alembic/versions/${NC}"
        echo -e "${BLUE}Next step: Run './migrate.sh upgrade' to apply it${NC}"
        ;;

    upgrade)
        run_migration "alembic upgrade head" \
                      "Applying all pending migrations..."
        echo
        echo -e "${GREEN}✅ Database schema updated${NC}"
        ;;

    downgrade)
        run_migration "alembic downgrade -1" \
                      "Rolling back last migration..."
        echo
        echo -e "${GREEN}✅ Migration rolled back${NC}"
        ;;

    history)
        run_migration "alembic history --verbose" \
                      "Migration history:"
        ;;

    current)
        run_migration "alembic current" \
                      "Current migration version:"
        ;;

    revision)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please provide a message for the migration${NC}"
            echo "Usage: ./migrate.sh revision \"Add new field\""
            exit 1
        fi
        run_migration "alembic revision --autogenerate -m \"$2\"" \
                      "Creating new migration..."
        echo
        echo -e "${GREEN}✅ Migration file created${NC}"
        ;;

    help|*)
        echo "Usage: ./migrate.sh [command]"
        echo
        echo "Commands:"
        echo "  init         - Generate initial migration from existing models"
        echo "  upgrade      - Apply all pending migrations"
        echo "  downgrade    - Rollback the last migration"
        echo "  revision MSG - Create a new migration with message"
        echo "  history      - Show migration history"
        echo "  current      - Show current migration version"
        echo "  help         - Show this help message"
        echo
        echo "Examples:"
        echo "  ./migrate.sh init              # First time setup"
        echo "  ./migrate.sh upgrade           # Apply migrations"
        echo "  ./migrate.sh revision \"Add Invoice Ninja fields\""
        ;;
esac
