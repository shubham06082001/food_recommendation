#!/bin/sh
set -e
# app.py starts the backend, waits for /health, then runs the dashboard.
exec python app.py
