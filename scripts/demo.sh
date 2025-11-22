#!/bin/bash
# Demo script for Meeting-to-Modules pipeline
# This script runs the complete pipeline on seed data and displays results

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Meeting-to-Modules Demo ===${NC}"
echo ""

# Step 1: Clean outputs
echo -e "${YELLOW}[1/7] Cleaning outputs...${NC}"
if [ -d "outputs" ]; then
    rm -rf outputs/*
    echo -e "${GREEN}✓ Outputs cleaned${NC}"
else
    echo -e "${GREEN}✓ Outputs directory doesn't exist (will be created)${NC}"
fi
echo ""

# Step 2: Initialize sample data
echo -e "${YELLOW}[2/7] Initializing sample data...${NC}"
mtm init-sample
echo -e "${GREEN}✓ Sample data initialized${NC}"
echo ""

# Step 3: Ingest notes
echo -e "${YELLOW}[3/7] Ingesting notes...${NC}"
mtm ingest
echo -e "${GREEN}✓ Notes ingested${NC}"
echo ""

# Step 4: Preprocess
echo -e "${YELLOW}[4/7] Preprocessing notes...${NC}"
mtm preprocess
echo -e "${GREEN}✓ Notes preprocessed${NC}"
echo ""

# Step 5: Analyze themes
echo -e "${YELLOW}[5/7] Analyzing themes...${NC}"
mtm analyze
echo -e "${GREEN}✓ Themes analyzed${NC}"
echo ""

# Step 6: Extract structured information
echo -e "${YELLOW}[6/7] Extracting structured information...${NC}"
mtm extract
echo -e "${GREEN}✓ Information extracted${NC}"
echo ""

# Step 7: Generate modules
echo -e "${YELLOW}[7/7] Generating modules...${NC}"
mtm generate
echo -e "${GREEN}✓ Modules generated${NC}"
echo ""

# Step 8: Export (optional, but included for completeness)
echo -e "${YELLOW}[8/8] Exporting knowledge base...${NC}"
mtm export --no-pdf 2>/dev/null || mtm export  # Try without PDF first, fallback to with PDF
echo -e "${GREEN}✓ Knowledge base exported${NC}"
echo ""

# Find index file
INDEX_FILE=""
if [ -d "outputs/modules" ]; then
    # Look for index.md files
    INDEX_FILE=$(find outputs/modules -name "index.md" -type f | head -n 1)
fi

# Print summary
echo -e "${BLUE}=== Summary ===${NC}"
echo ""

# Count notes
NOTES_COUNT=$(mtm list --themes 2>/dev/null | grep -c "Theme" || echo "0")
if [ "$NOTES_COUNT" = "0" ]; then
    # Try alternative method
    NOTES_COUNT=$(sqlite3 outputs/mtm.db "SELECT COUNT(*) FROM notes;" 2>/dev/null || echo "0")
fi

# Count themes
THEMES_COUNT=$(mtm list --themes 2>/dev/null | tail -n +3 | wc -l || echo "0")
if [ "$THEMES_COUNT" = "0" ]; then
    THEMES_COUNT=$(sqlite3 outputs/mtm.db "SELECT COUNT(*) FROM themes;" 2>/dev/null || echo "0")
fi

# Count modules
MODULES_COUNT=$(mtm list --modules 2>/dev/null | tail -n +3 | wc -l || echo "0")
if [ "$MODULES_COUNT" = "0" ]; then
    MODULES_COUNT=$(sqlite3 outputs/mtm.db "SELECT COUNT(*) FROM modules;" 2>/dev/null || echo "0")
fi

# Count generated files
if [ -d "outputs/modules" ]; then
    FILES_COUNT=$(find outputs/modules -name "*.md" -type f | wc -l)
else
    FILES_COUNT="0"
fi

echo -e "${GREEN}Notes processed:${NC} $NOTES_COUNT"
echo -e "${GREEN}Themes identified:${NC} $THEMES_COUNT"
echo -e "${GREEN}Modules generated:${NC} $MODULES_COUNT"
echo -e "${GREEN}Markdown files created:${NC} $FILES_COUNT"
echo ""

# Display index path hint
if [ -n "$INDEX_FILE" ] && [ -f "$INDEX_FILE" ]; then
    echo -e "${BLUE}=== Index File ===${NC}"
    echo -e "${GREEN}Main index:${NC} $INDEX_FILE"
    echo ""
    echo -e "${YELLOW}To view the index, run:${NC}"
    echo -e "  ${BLUE}cat \"$INDEX_FILE\"${NC}"
    echo ""
    
    # Try to open the index (platform-specific)
    if command -v xdg-open > /dev/null; then
        # Linux
        echo -e "${YELLOW}Opening index in default application...${NC}"
        xdg-open "$INDEX_FILE" 2>/dev/null || true
    elif command -v open > /dev/null; then
        # macOS
        echo -e "${YELLOW}Opening index in default application...${NC}"
        open "$INDEX_FILE" 2>/dev/null || true
    elif command -v start > /dev/null; then
        # Windows (Git Bash)
        echo -e "${YELLOW}Opening index in default application...${NC}"
        start "$INDEX_FILE" 2>/dev/null || true
    else
        echo -e "${YELLOW}Please open the index file manually:${NC}"
        echo -e "  ${BLUE}$INDEX_FILE${NC}"
    fi
else
    echo -e "${YELLOW}No index file found. Generated files are in:${NC}"
    echo -e "  ${BLUE}outputs/modules/${NC}"
    echo ""
    if [ -d "outputs/modules" ]; then
        echo -e "${GREEN}Available module files:${NC}"
        find outputs/modules -name "*.md" -type f | head -n 10
        if [ "$FILES_COUNT" -gt 10 ]; then
            echo -e "${YELLOW}... and $((FILES_COUNT - 10)) more${NC}"
        fi
    fi
fi

echo ""
echo -e "${GREEN}=== Demo Complete ===${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  - Explore generated modules in outputs/modules/"
echo "  - Check exports in outputs/exports/"
echo "  - View logs in outputs/logs/"
echo "  - Run 'mtm verify' to check system integrity"
echo "  - Run 'mtm search <query>' to search the knowledge base"
echo ""

