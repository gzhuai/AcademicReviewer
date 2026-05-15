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
echo -e "${WHITE}      AcademicReviewer -- Backend (FastAPI)${NC}"
echo -e "${CYAN}  ================================================${NC}"
echo ""
echo -e "${YELLOW}  Starting backend server...${NC}"
echo -e "${WHITE}  API:  http://127.0.0.1:8000${NC}"
echo -e "${WHITE}  Docs: http://127.0.0.1:8000/docs${NC}"
echo ""

source venv/bin/activate
python run.py
