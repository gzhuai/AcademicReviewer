#!/usr/bin/env bash

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'

cd "$(dirname "$0")/.."

if [[ ! -f "venv/bin/activate" ]]; then
    echo -e "${RED}[X] Virtual environment not found. Please run install first:${NC}"
    echo -e "${YELLOW}    bash scripts/install.sh${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}  ================================================${NC}"
echo -e "${WHITE}      AcademicReviewer -- Frontend (Gradio)${NC}"
echo -e "${CYAN}  ================================================${NC}"
echo ""
echo -e "${YELLOW}  Starting Gradio UI...${NC}"
echo -e "${WHITE}  URL: http://127.0.0.1:7860${NC}"
echo ""

source venv/bin/activate
python app/gradio_app.py
