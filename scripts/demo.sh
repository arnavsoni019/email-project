#!/usr/bin/env bash
# Run mailorg against the synthetic demo mailbox.
#
#   scripts/demo.sh seed     rebuild data/demo.db (+ vector index)
#   scripts/demo.sh start    run the API on the demo data, and Vite
#   scripts/demo.sh stop     stop both
#   scripts/demo.sh real     stop the demo API and start it on the real mailbox
#
# The demo lives in data/demo.db and data/demo_chroma. The real mailbox is never
# opened: mailorg.demo.seed refuses to run unless both paths contain "demo".
set -euo pipefail
cd "$(dirname "$0")/.."

export DB_PATH=data/demo.db
export CHROMA_PATH=data/demo_chroma

PY=.venv/bin/python
RUN=.run
mkdir -p "$RUN"

api_pid()  { [ -f "$RUN/api.pid" ]  && cat "$RUN/api.pid";  }
vite_pid() { [ -f "$RUN/vite.pid" ] && cat "$RUN/vite.pid"; }

# Kill by recorded pid only. Never `pkill -f uvicorn` — the pattern matches the
# shell running it and takes down this script with it.
stop_one() {
  local pid; pid=$(cat "$1" 2>/dev/null || true)
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then kill "$pid"; fi
  rm -f "$1"
}

start_api() {
  setsid nohup $PY -m uvicorn mailorg.web.api:app --host 127.0.0.1 --port 8000 \
    > "$RUN/api.log" 2>&1 < /dev/null &
  echo $! > "$RUN/api.pid"
  sleep 4
}

case "${1:-start}" in
  seed)
    $PY -m mailorg.demo.seed --index
    ;;
  start)
    stop_one "$RUN/api.pid"
    [ -f data/demo.db ] || $PY -m mailorg.demo.seed --index
    start_api
    if ! curl -sf -o /dev/null --max-time 3 http://localhost:5173/; then
      setsid nohup flatpak-spawn --host sh -c "cd $PWD/frontend && npm run dev" \
        > "$RUN/vite.log" 2>&1 < /dev/null &
      echo $! > "$RUN/vite.pid"
      sleep 5
    fi
    echo "Demo running — http://localhost:5173  (account: arjun.mehta@zephyrmail.com)"
    ;;
  stop)
    stop_one "$RUN/api.pid"; stop_one "$RUN/vite.pid"
    echo "Stopped."
    ;;
  real)
    stop_one "$RUN/api.pid"
    unset DB_PATH CHROMA_PATH
    start_api
    echo "Back on the real mailbox — http://localhost:5173"
    ;;
  *)
    echo "usage: scripts/demo.sh {seed|start|stop|real}" >&2; exit 1 ;;
esac
