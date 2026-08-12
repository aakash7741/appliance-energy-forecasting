#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -e .
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.7.1
python -m pip install chronos-forecasting==1.5.3 transformers==4.48.3 accelerate==1.3.0

