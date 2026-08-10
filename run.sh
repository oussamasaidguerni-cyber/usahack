#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "[run.sh] creating virtual environment..."
    python3 -m venv venv
fi
./venv/bin/pip install -q -r requirements.txt

stop() {
    if [ -f .usahack.pid ]; then
        PID=$(cat .usahack.pid)
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "[run.sh] stopped background server (pid $PID)"
        fi
        rm -f .usahack.pid
    else
        echo "[run.sh] no background server running"
    fi
}

case "${1:-}" in
    bg)
        stop
        nohup ./venv/bin/python app.py > server.log 2>&1 &
        echo $! > .usahack.pid
        sleep 1
        echo "[run.sh] server started in background - http://127.0.0.1:5000"
        echo "[run.sh] logs: server.log | stop it with: ./run.sh stop"
        ;;
    stop)
        stop
        ;;
    *)
        echo "[run.sh] starting (Ctrl+C to stop, it restarts on crash)"
        echo "[run.sh] open http://127.0.0.1:5000"
        while true; do
            ./venv/bin/python app.py
            echo "[run.sh] server stopped (exit $?) - restarting in 2s... (Ctrl+C to quit)"
            sleep 2
        done
        ;;
esac
