#!/usr/bin/env bash

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'

cd "$(dirname "$0")/.."

if [[ ! -f "venv/bin/activate" ]]; then
    echo -e "${RED}[X] Virtual environment not found. Please run install first:${NC}"
    echo -e "${YELLOW}    bash scripts/install.sh${NC}"
    exit 1
fi

# ── Detect whether we have a GUI terminal ──
HAS_GUI=false
if [[ "$OSTYPE" == "darwin"* ]] && command -v osascript &>/dev/null; then
    HAS_GUI=true
elif command -v gnome-terminal &>/dev/null; then
    HAS_GUI=true
elif command -v xterm &>/dev/null; then
    HAS_GUI=true
fi

if $HAS_GUI; then
    # ── GUI mode: open new terminal windows ──
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
else
    # ── Headless / SSH / WSL mode: background processes ──
    echo -e "${YELLOW}[!] No GUI terminal detected (SSH / WSL / headless server).${NC}"
    echo -e "${YELLOW}    Starting services as background processes...${NC}"
    echo ""

    source venv/bin/activate

    echo -e "${GREEN}Starting backend (FastAPI on :8000)...${NC}"
    python run.py > /tmp/academic_reviewer_backend.log 2>&1 &
    BACKEND_PID=$!
    echo -e "    Backend PID: $BACKEND_PID  (log: /tmp/academic_reviewer_backend.log)"

    sleep 3

    echo -e "${GREEN}Starting frontend (Gradio on :7860)...${NC}"
    python app/gradio_app.py > /tmp/academic_reviewer_frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo -e "    Frontend PID: $FRONTEND_PID  (log: /tmp/academic_reviewer_frontend.log)"

    sleep 5
fi

# ── Open browser ──
echo -e "${GREEN}Opening browser...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://127.0.0.1:7860"
else
    xdg-open "http://127.0.0.1:7860" 2>/dev/null || echo "Please open http://127.0.0.1:7860 in your browser"
fi

echo ""
echo -e "${CYAN}  ================================================${NC}"
echo -e "${WHITE}    Frontend: http://127.0.0.1:7860${NC}"
echo -e "${WHITE}    Backend:  http://127.0.0.1:8000/docs${NC}"
echo -e "${CYAN}  ================================================${NC}"

if ! $HAS_GUI; then
    echo ""
    echo -e "${YELLOW}  Services running in background. To stop:${NC}"
    echo -e "${WHITE}    kill $BACKEND_PID $FRONTEND_PID${NC}"
    echo -e "${YELLOW}  Or press Ctrl+C (if running in foreground).${NC}"
    echo ""
    # Wait for user Ctrl+C
    trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
    wait
else
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
fi
