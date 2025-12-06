#!/bin/bash

# Flutter Test Coverage Script for SomniProperty
# Generates test coverage report and checks thresholds

set -e

echo "========================================"
echo "Flutter Test Coverage Report"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Flutter is installed
if ! command -v flutter &> /dev/null; then
    echo -e "${RED}Error: Flutter command not found${NC}"
    echo "Please install Flutter SDK"
    exit 1
fi

# Run tests with coverage
echo "Running Flutter tests with coverage..."
flutter test --coverage || {
    echo -e "${RED}Tests failed!${NC}"
    exit 1
}

# Check if lcov is installed
if ! command -v lcov &> /dev/null; then
    echo -e "${YELLOW}Warning: lcov not installed. Skipping HTML report generation.${NC}"
    echo "Install lcov to generate HTML reports:"
    echo "  - Ubuntu/Debian: sudo apt-get install lcov"
    echo "  - macOS: brew install lcov"
    exit 0
fi

# Generate HTML report
echo ""
echo "Generating HTML coverage report..."
genhtml coverage/lcov.info -o coverage/html --quiet

echo -e "${GREEN}✓ HTML report generated at: coverage/html/index.html${NC}"

# Calculate coverage percentage
COVERAGE=$(lcov --summary coverage/lcov.info 2>&1 | grep "lines" | awk '{print $2}' | sed 's/%//')

echo ""
echo "========================================"
echo "Coverage Summary"
echo "========================================"
echo "Total Coverage: ${COVERAGE}%"

# Check against threshold (80%)
THRESHOLD=80

if (( $(echo "$COVERAGE >= $THRESHOLD" | bc -l) )); then
    echo -e "${GREEN}✓ Coverage meets threshold (>= ${THRESHOLD}%)${NC}"
    EXIT_CODE=0
else
    echo -e "${RED}✗ Coverage below threshold (< ${THRESHOLD}%)${NC}"
    EXIT_CODE=1
fi

# Module-specific coverage (if lcov_cobertura is available)
echo ""
echo "Module Coverage:"
echo "  - Properties: Target 80%+"
echo "  - Tenants: Target 80%+"
echo "  - Leases: Target 80%+"
echo "  - Payments: Target 80%+"
echo "  - Work Orders: Target 80%+"
echo ""

echo "To view detailed report:"
echo "  open coverage/html/index.html  (macOS)"
echo "  xdg-open coverage/html/index.html  (Linux)"
echo "  start coverage/html/index.html  (Windows)"

exit $EXIT_CODE
