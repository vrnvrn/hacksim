#!/usr/bin/env bash
# HackSim live demo: orchestrator + frontend together.
#
# Boots the FastAPI orchestrator in HACKSIM_AUTO_START=true mode, boots
# the Next.js dev server pointed at the orchestrator (no mocks), opens
# the browser. Ctrl-C cleans up both, plus any AXL nodes still running.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

VENV_PY="${REPO_ROOT}/.venv/bin/python"
VENV_UVICORN="${REPO_ROOT}/.venv/bin/uvicorn"
AXL_BIN="${REPO_ROOT}/third_party/axl/node"

ORCH_PORT="${HACKSIM_ORCH_PORT:-8000}"
WEB_PORT="${HACKSIM_WEB_PORT:-3000}"
PACE="${HACKSIM_PACE:-quick}"

if [ ! -x "${VENV_PY}" ]; then
  echo "Python venv not found at ${REPO_ROOT}/.venv. Run 'python3 -m venv .venv && .venv/bin/pip install -e .[dev,orchestrator,agents] fastapi uvicorn[standard] httpx anthropic' first." >&2
  exit 1
fi

if [ ! -x "${AXL_BIN}" ]; then
  echo "AXL binary not built. Running scripts/build_axl.sh ..."
  bash "${REPO_ROOT}/scripts/build_axl.sh"
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm not on PATH. Install pnpm or use a Node version manager that ships it." >&2
  exit 1
fi

if [ ! -d "${REPO_ROOT}/apps/web/node_modules" ]; then
  echo "apps/web/node_modules missing. Running pnpm install ..."
  (cd "${REPO_ROOT}/apps/web" && pnpm install)
fi

# Pre-flight cleanup: anything left over from a previous run.
pkill -f "uvicorn .*orchestrator.api" 2>/dev/null || true
pkill -f "third_party/axl/node" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 1

echo ""
echo "=== HackSim live demo ==="
echo "  orchestrator: http://127.0.0.1:${ORCH_PORT}"
echo "  frontend:     http://127.0.0.1:${WEB_PORT}"
echo "  pace:         ${PACE}"
echo ""

# Start the orchestrator.
ORCH_LOG="${REPO_ROOT}/sim-runs/orchestrator.log"
mkdir -p "${REPO_ROOT}/sim-runs"
HACKSIM_AUTO_START=true \
HACKSIM_AXL_BIN="${AXL_BIN}" \
HACKSIM_RUNS_DIR="${REPO_ROOT}/sim-runs" \
HACKSIM_ORCH_URL="http://127.0.0.1:${ORCH_PORT}" \
HACKSIM_PACE="${PACE}" \
"${VENV_UVICORN}" packages.orchestrator.api:app \
  --host 127.0.0.1 --port "${ORCH_PORT}" \
  > "${ORCH_LOG}" 2>&1 &
ORCH_PID=$!
echo "started orchestrator (pid ${ORCH_PID}, log ${ORCH_LOG})"

# Wait for orchestrator readiness.
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${ORCH_PORT}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
if ! curl -fsS "http://127.0.0.1:${ORCH_PORT}/api/health" >/dev/null 2>&1; then
  echo "orchestrator did not become healthy in time. tail of log:" >&2
  tail -20 "${ORCH_LOG}" >&2
  kill "${ORCH_PID}" 2>/dev/null || true
  exit 1
fi
echo "orchestrator is healthy"

# Start the frontend pointed at the live orchestrator.
WEB_LOG="${REPO_ROOT}/sim-runs/web.log"
(
  cd "${REPO_ROOT}/apps/web"
  NEXT_PUBLIC_USE_MOCKS=false \
  ORCHESTRATOR_BASE_URL="http://127.0.0.1:${ORCH_PORT}" \
  pnpm dev --port "${WEB_PORT}" > "${WEB_LOG}" 2>&1 &
  echo $! > /tmp/hacksim_web.pid
)
WEB_PID="$(cat /tmp/hacksim_web.pid)"
echo "started frontend (pid ${WEB_PID}, log ${WEB_LOG})"

# Wait for the web server.
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${WEB_PORT}/" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
if ! curl -fsS "http://127.0.0.1:${WEB_PORT}/" >/dev/null 2>&1; then
  echo "frontend did not become ready in time. tail of log:" >&2
  tail -30 "${WEB_LOG}" >&2
  kill "${ORCH_PID}" "${WEB_PID}" 2>/dev/null || true
  exit 1
fi
echo "frontend is ready"

# Open the browser. macOS uses `open`; Linux uses `xdg-open` if present.
if command -v open >/dev/null 2>&1; then
  open "http://127.0.0.1:${WEB_PORT}/"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:${WEB_PORT}/" >/dev/null 2>&1 &
fi

echo ""
echo "=== ready ==="
echo "  hero:  http://127.0.0.1:${WEB_PORT}/"
echo "  health: http://127.0.0.1:${ORCH_PORT}/api/health"
echo ""
echo "Type a prompt and click 'Spin up sim'. Watch the live page; the SSE"
echo "stream replays envelopes from the spawned mesh."
echo ""
echo "Ctrl-C to stop."

cleanup() {
  echo ""
  echo "shutting down ..."
  pkill -f "next dev" 2>/dev/null || true
  pkill -f "uvicorn .*orchestrator.api" 2>/dev/null || true
  pkill -f "third_party/axl/node" 2>/dev/null || true
  rm -f /tmp/hacksim_web.pid 2>/dev/null || true
  sleep 1
  echo "done."
}
trap cleanup EXIT INT TERM

# Block until the user hits Ctrl-C. We do not use `wait -n` because
# pnpm forks a child and the parent shell can exit while the dev server
# keeps running, which would confuse the trap. A periodic health probe
# bails out if either process actually dies.
while true; do
  sleep 5
  if ! curl -fsS "http://127.0.0.1:${ORCH_PORT}/api/health" >/dev/null 2>&1; then
    echo "orchestrator is unreachable. tail of log:" >&2
    tail -10 "${ORCH_LOG}" >&2
    exit 1
  fi
  if ! curl -fsS -o /dev/null "http://127.0.0.1:${WEB_PORT}/" 2>/dev/null; then
    echo "frontend is unreachable. tail of log:" >&2
    tail -10 "${WEB_LOG}" >&2
    exit 1
  fi
done
