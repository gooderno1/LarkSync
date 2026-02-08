#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
APP_BUNDLE="$DIST_DIR/LarkSync/LarkSync.app"

if ! command -v create-dmg >/dev/null 2>&1; then
  echo "ERROR: create-dmg not found. Install with: brew install create-dmg"
  exit 1
fi

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "ERROR: .app bundle not found: $APP_BUNDLE"
  exit 1
fi

APP_VERSION="${APP_VERSION:-}"
if [[ -z "$APP_VERSION" ]]; then
  APP_VERSION="$(
    LARKSYNC_ROOT="$ROOT_DIR" python - <<'PY'
import os
import re
from pathlib import Path

root = Path(os.environ.get("LARKSYNC_ROOT", ".")).resolve()
pyproject = root / "apps" / "backend" / "pyproject.toml"
if not pyproject.is_file():
    print("0.0.0")
    raise SystemExit
content = pyproject.read_text(encoding="utf-8")
match = re.search(r'^version\\s*=\\s*\"([^\"]+)\"', content, re.MULTILINE)
print(match.group(1) if match else "0.0.0")
PY
  )"
fi

DMG_NAME="LarkSync-${APP_VERSION}.dmg"
OUTPUT_PATH="$DIST_DIR/$DMG_NAME"

create-dmg \
  --volname "LarkSync" \
  --window-size 600 400 \
  --icon-size 100 \
  --app-drop-link 450 200 \
  --icon "LarkSync.app" 150 200 \
  "$OUTPUT_PATH" \
  "$APP_BUNDLE"

echo "OK: DMG created at $OUTPUT_PATH"
