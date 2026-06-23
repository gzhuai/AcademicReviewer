#!/usr/bin/env bash

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; GRAY='\033[0;90m'; NC='\033[0m'

cd "$(dirname "$0")/.."

echo ""
echo -e "${CYAN}  ================================================${NC}"
echo -e "${WHITE}      AcademicReviewer -- One-Click Install${NC}"
echo -e "${CYAN}  ================================================${NC}"
echo ""

echo -e "${YELLOW}[Pre-check] Checking disk space (>= 2 GB required)...${NC}"
free_kb=$(df -k "$PWD" 2>/dev/null | tail -1 | awk '{print $4}')
if [[ -n "$free_kb" ]] && [[ "$free_kb" -lt 2000000 ]]; then
    free_gb=$(echo "scale=1; $free_kb/1024/1024" | bc 2>/dev/null || echo "?")
    echo -e "${RED}  [X] Only ${free_gb} GB free (need >= 2 GB). The venv will be ~800 MB.${NC}"
    echo -e "${RED}      Please free up space and retry.${NC}"
    read -r -p "Press Enter to exit"
    exit 1
fi
echo -e "${GREEN}   Disk space OK${NC}"

echo ""
echo -e "${YELLOW}[1/5] Checking Python environment...${NC}"

PYTHON_CMD=""
for cmd in python3 python3.12 python3.11 python3.10 python; do
    if command -v "$cmd" &>/dev/null; then
        major=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null)
        minor=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null)
        if [[ "$major" -ge 3 && "$minor" -ge 10 ]]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo ""
    echo -e "${RED}  [X] Python 3.10+ not found!${NC}"
    echo ""
    echo -e "${YELLOW}  Please install Python 3.10 or newer:${NC}"
    echo -e "${WHITE}    macOS:  brew install python@3.12${NC}"
    echo -e "${WHITE}    Ubuntu: sudo apt install python3.12 python3.12-venv${NC}"
    echo -e "${WHITE}    Or:     https://www.python.org/downloads/${NC}"
    echo ""
    read -r -p "Press Enter to exit"
    exit 1
fi

echo -e "${GREEN}   Python: $PYTHON_CMD ($($PYTHON_CMD --version))  OK${NC}"

echo ""
echo -e "${YELLOW}[2/5] Creating virtual environment...${NC}"

if [[ -f "venv/bin/activate" ]]; then
    echo -e "${GRAY}   venv already exists, skipping.${NC}"
else
    $PYTHON_CMD -m venv venv
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}   [X] Failed to create virtual environment.${NC}"
        echo -e "${GRAY}   Ensure $PYTHON_CMD has the 'venv' module installed.${NC}"
        read -r -p "Press Enter to exit"
        exit 1
    fi
    echo -e "${GREEN}   venv created  OK${NC}"
fi

echo ""
echo -e "${YELLOW}[3/5] Installing dependencies (may take a few minutes)...${NC}"

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
if [[ $? -ne 0 ]]; then
    echo -e "${RED}   [X] pip install failed! Check your network and retry.${NC}"
    echo -e "${GRAY}   You can retry:  bash scripts/install.sh${NC}"
    read -r -p "Press Enter to exit"
    exit 1
fi
echo -e "${GREEN}   Dependencies installed  OK${NC}"

echo ""
echo -e "${YELLOW}[4/5] Configuring environment...${NC}"

if [[ -f ".env" ]]; then
    echo -e "${GRAY}   .env already exists, skipping.${NC}"
else
    cp .env.example .env
    echo -e "${GREEN}   .env created from .env.example  OK${NC}"
fi

echo ""
echo -e "${YELLOW}[5/5] Creating data directories...${NC}"

mkdir -p data/calibration/winners
mkdir -p data/calibration/losers
mkdir -p data/calibration/external
echo -e "${GREEN}   Data directories ready  OK${NC}"

echo ""
echo -e "${GREEN}  ================================================${NC}"
echo -e "${WHITE}             Installation Complete!${NC}"
echo -e "${GREEN}  ================================================${NC}"
echo ""
echo -e "${WHITE}  Next steps:${NC}"
echo -e "${YELLOW}    1. Edit .env and fill in at least one API Key:${NC}"
echo -e "${WHITE}       nano .env${NC}"
echo -e "${YELLOW}    2. Start all services:${NC}"
echo -e "${WHITE}       bash scripts/start_all.sh${NC}"
echo ""

read -r -p "Edit .env now? (y/n) " edit
if [[ "$edit" == "y" || "$edit" == "Y" ]]; then
    if command -v nano &>/dev/null; then
        nano .env
    elif command -v vim &>/dev/null; then
        vim .env
    else
        open .env 2>/dev/null || xdg-open .env 2>/dev/null || echo "Please open .env manually with a text editor"
    fi
    echo ""
    echo -e "${YELLOW}After saving, press Enter to continue...${NC}"
    read -r
fi

echo ""
echo -e "${GREEN}All ready! Run:  bash scripts/start_all.sh${NC}"
echo ""
