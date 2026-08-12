#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/.analysis_packages:$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export MPLCONFIGDIR="$ROOT/.cache/matplotlib"
export HF_HOME="$ROOT/.cache/huggingface"
mkdir -p "$MPLCONFIGDIR" "$HF_HOME"
python "$ROOT/scripts/run_pipeline.py"
