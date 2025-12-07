#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================="
echo "  DragonSync Configuration Setup"
echo "========================================="
echo ""

# Function to setup a config file
setup_config() {
    local example_file=$1
    local config_file=$2
    local config_name=$3

    if [ ! -f "$config_file" ]; then
        # Config doesn't exist, create it from example
        echo -e "${GREEN}✓${NC} Creating ${config_name} from ${example_file}..."
        cp "$example_file" "$config_file"
        echo -e "  ${BLUE}→${NC} Please edit ${config_file} to customize your settings"
        echo ""
    else
        # Config exists, show differences
        echo -e "${YELLOW}!${NC} ${config_name} already exists"

        # Check if there are differences
        if diff -q "$example_file" "$config_file" > /dev/null 2>&1; then
            echo -e "  ${GREEN}→${NC} Your config matches the example (no changes needed)"
            echo ""
        else
            echo -e "  ${BLUE}→${NC} Showing differences between example and your config:"
            echo -e "  ${BLUE}→${NC} Lines with ${GREEN}+${NC} are in the example but not in your config"
            echo -e "  ${BLUE}→${NC} Lines with ${YELLOW}-${NC} are in your config but not in the example"
            echo ""
            echo "========================================="

            # Show side-by-side diff with color
            if command -v colordiff &> /dev/null; then
                diff -u "$config_file" "$example_file" | colordiff | tail -n +3
            else
                diff -u "$config_file" "$example_file" | tail -n +3
            fi

            echo "========================================="
            echo -e "  ${YELLOW}→${NC} Review the differences above and update ${config_file} if needed"
            echo ""
        fi
    fi
}

# Setup config.ini
if [ -f "config-example.ini" ]; then
    setup_config "config-example.ini" "config.ini" "config.ini"
else
    echo -e "${YELLOW}⚠${NC} Warning: config-example.ini not found"
    echo ""
fi

# Setup gps.ini
if [ -f "gps-example.ini" ]; then
    setup_config "gps-example.ini" "gps.ini" "gps.ini"
else
    echo -e "${YELLOW}⚠${NC} Warning: gps-example.ini not found"
    echo ""
fi

echo "========================================="
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit config.ini to configure your settings"
echo "  2. Edit gps.ini to configure GPS (if needed)"
echo "  3. Run DragonSync with your custom configuration"
echo "========================================="
