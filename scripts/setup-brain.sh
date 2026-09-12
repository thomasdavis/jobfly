#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export FLY_DATA="${FLY_DATA:-/mnt/donto-data/donto-resources/research/jobfly-runtime/brain}"
mkdir -p "$FLY_DATA"
.venv/bin/python backend/vendor/fly_ai/build_brain.py
