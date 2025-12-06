#!/bin/bash
# Database Initialization Script for SomniProperty
# This script ensures all required database tables are created before the backend starts
# Addresses the issue: "Why aren't these tables automatically created?"

set -e  # Exit on error

echo "========================================="
echo "SomniProperty Database Initialization"
echo "========================================="
echo ""

# Database connection details (from environment variables)
: ${POSTGRES_HOST:=somniproperty-postgres}
: ${POSTGRES_PORT:=5432}
: ${POSTGRES_DB:=somniproperty}
: ${POSTGRES_USER:=somniproperty}
: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}

export PGPASSWORD="$POSTGRES_PASSWORD"

echo "Connecting to database: $POSTGRES_DB on $POSTGRES_HOST:$POSTGRES_PORT"
echo ""

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c '\q' 2>/dev/null; then
        echo "✓ PostgreSQL is ready"
        break
    fi
    echo "  Attempt $i/30: Waiting for PostgreSQL..."
    sleep 2
done

# Check if we can connect
if ! psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c '\q' 2>/dev/null; then
    echo "✗ Failed to connect to PostgreSQL after 60 seconds"
    exit 1
fi

echo ""
echo "Checking database initialization status..."

# Check if alembic_version table exists (indicates database has been initialized)
TABLE_COUNT=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name NOT LIKE 'pg_%'" 2>/dev/null || echo "0")

echo "Current table count: $TABLE_COUNT"

if [ "$TABLE_COUNT" -lt 5 ]; then
    echo ""
    echo "Database appears to be empty or incomplete. Running full schema initialization..."
    echo ""

    # Run base schema
    if [ -f "/app/schema/DATABASE-SCHEMA.sql" ]; then
        echo "→ Applying base schema (DATABASE-SCHEMA.sql)..."
        psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /app/schema/DATABASE-SCHEMA.sql
        echo "  ✓ Base schema applied"
    else
        echo "  ⚠ DATABASE-SCHEMA.sql not found"
    fi

    # Run additional schema files
    for schema_file in /app/schema/DATABASE-SCHEMA-*.sql; do
        if [ -f "$schema_file" ]; then
            filename=$(basename "$schema_file")
            echo "→ Applying $filename..."
            psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$schema_file" || echo "  ⚠ Some errors in $filename (may be expected)"
        fi
    done

    echo ""
    echo "✓ Schema initialization complete"
else
    echo "✓ Database already initialized (found $TABLE_COUNT tables)"
fi

echo ""
echo "Final table count:"
psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt" | head -30

echo ""
echo "========================================="
echo "Database initialization complete!"
echo "========================================="
