#!/bin/bash

# Preflight checks
python -m compileall -q /app || exit 1
python -c "import importlib; importlib.import_module(\'app\')" || exit 1

# Start gunicorn
exec gunicorn --bind 0.0.0.0:8080 --workers 1 --threads --preload app:app
