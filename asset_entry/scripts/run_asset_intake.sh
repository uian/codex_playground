#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/uian/Documents/Playground/asset_entry"
CONFIG="$ROOT/config/config.yaml"
OUTPUT="$ROOT/output"

usage() {
  cat <<'EOF'
Usage:
  run_asset_intake.sh prepare <device-list-file>
  run_asset_intake.sh fill

Modes:
  prepare   OCR the device list and build intake rows
  fill      Launch browser autofill up to manual submit
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

mode="$1"
shift || true

case "$mode" in
  prepare)
    if [[ $# -ne 1 ]]; then
      usage
      exit 1
    fi
    input_file="$1"
    python3 "$ROOT/scripts/ocr_extract.py" "$input_file" --out "$OUTPUT"
    python3 "$ROOT/scripts/build_intake.py" "$OUTPUT/parsed_items.json" --config "$CONFIG" --out "$OUTPUT"
    ;;
  fill)
    python3 "$ROOT/scripts/playwright_fill.py" --config "$CONFIG" --input "$OUTPUT/intake_rows.json"
    ;;
  *)
    usage
    exit 1
    ;;
esac
