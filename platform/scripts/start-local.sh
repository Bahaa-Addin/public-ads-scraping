#!/usr/bin/env bash
# ============================================================================
# Agentic Ads Platform - Start All Local Services
# ============================================================================
# Starts the agent, dashboard backend, and dashboard frontend locally.
#
# Usage:
#   ./scripts/start-local.sh           # Start all services
#   ./scripts/start-local.sh --agent   # Agent only
#   ./scripts/start-local.sh --dash    # Dashboard only (backend + frontend)
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }

cleanup() {
    log_info "Stopping all services..."
    kill $AGENT_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

cd "$PROJECT_ROOT"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       CREATIVE ADS PLATFORM - LOCAL DEVELOPMENT             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

START_AGENT=true
START_DASH=true

if [ "$1" == "--agent" ]; then
    START_DASH=false
elif [ "$1" == "--dash" ]; then
    START_AGENT=false
fi

# ============================================================================
# Start Agent Brain (Port 8081)
# ============================================================================

if [ "$START_AGENT" == "true" ]; then
    log_info "Starting Agent Brain on port 8081..."
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    # Start the agent API in background
    MODE=local python -c "
import asyncio
import uvicorn
from agent.api import app

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8081, log_level='info')
" &
    AGENT_PID=$!
    
    sleep 2
    if ps -p $AGENT_PID > /dev/null 2>&1; then
        log_success "Agent Brain started (PID: $AGENT_PID)"
        log_info "  API: http://localhost:8081"
        log_info "  Docs: http://localhost:8081/docs"
    else
        log_warn "Agent Brain failed to start"
    fi
fi

# ============================================================================
# Start Dashboard Backend (Port 8000)
# ============================================================================

if [ "$START_DASH" == "true" ]; then
    log_info "Starting Dashboard Backend on port 8000..."
    
    cd "$PROJECT_ROOT/dashboard/backend"
    source venv/bin/activate
    
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    
    sleep 2
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        log_success "Dashboard Backend started (PID: $BACKEND_PID)"
        log_info "  API: http://localhost:8000"
        log_info "  Docs: http://localhost:8000/docs"
    else
        log_warn "Dashboard Backend failed to start"
    fi
    
    # ============================================================================
    # Start Dashboard Frontend (Port 5173)
    # ============================================================================
    
    log_info "Starting Dashboard Frontend on port 5173..."
    
    cd "$PROJECT_ROOT/dashboard/frontend"
    npm run dev &
    FRONTEND_PID=$!
    
    sleep 3
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        log_success "Dashboard Frontend started (PID: $FRONTEND_PID)"
        log_info "  UI: http://localhost:5173"
    else
        log_warn "Dashboard Frontend failed to start"
    fi
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    ALL SERVICES RUNNING                        ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""

if [ "$START_AGENT" == "true" ]; then
    echo "  Agent API:          http://localhost:8081"
    echo "  Agent Docs:         http://localhost:8081/docs"
fi

if [ "$START_DASH" == "true" ]; then
    echo "  Dashboard Backend:  http://localhost:8000"
    echo "  Dashboard Docs:     http://localhost:8000/docs"
    echo "  Dashboard UI:       http://localhost:5173"
fi

echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait

