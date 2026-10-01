#!/usr/bin/env bash
# Start PriceWatch locally: ./run.sh   then open http://localhost:8003
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Creating virtual environment and installing packages (first run only)..."
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt
fi
[ -f .env ] || cp .env.example .env
export PORT="${PORT:-8003}"
echo "PriceWatch running at http://localhost:$PORT  (landing: /landing). The demo store is created on first start (~10 s)."
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
