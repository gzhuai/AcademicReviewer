#!/usr/bin/env bash

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'

cd "$(dirname "$0")/.."

if [[ ! -f "venv/bin/activate" ]]; then
    echo -e "${RED}[X] Virtual environment not found. Please run install first:${NC}"
    echo -e "${YELLOW}    bash scripts/install.sh${NC}"
    exit 1
fi

echo -e "${GREEN}Starting backend (waiting for initialization)...${NC}"

if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "tell app \"Terminal\" to do script \"cd \\\"$PWD\\\" && bash scripts/start_backend.sh\"" 2>/dev/null
elif command -v gnome-terminal &>/dev/null; then
    gnome-terminal -- bash -c "cd '$PWD' && bash scripts/start_backend.sh; exec bash" 2>/dev/null
else
    xterm -e "cd '$PWD' && bash scripts/start_backend.sh; bash" 2>/dev/null &
fi

sleep 5

echo -e "${GREEN}Starting frontend...${NC}"

if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "tell app \"Terminal\" to do script \"cd \\\"$PWD\\\" && bash scripts/start_frontend.sh\"" 2>/dev/null
elif command -v gnome-terminal &>/dev/null; then
    gnome-terminal -- bash -c "cd '$PWD' && bash scripts/start_frontend.sh; exec bash" 2>/dev/null
else
    xterm -e "cd '$PWD' && bash scripts/start_frontend.sh; bash" 2>/dev/null &
fi

sleep 8

echo -e "${GREEN}Opening browser...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://127.0.0.1:7860"
else
    xdg-open "http://127.0.0.1:7860" 2>/dev/null || echo "Please open http://127.0.0.1:7860 in your browser"
fi

echo -e "${CYAN}Frontend: http://127.0.0.1:7860${NC}"
echo -e "${CYAN}Backend:  http://127.0.0.1:8000/docs${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
