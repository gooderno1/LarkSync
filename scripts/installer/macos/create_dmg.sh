#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
APP_BUNDLE="${APP_BUNDLE:-$DIST_DIR/LarkSync.app}"
if [[ ! -d "$APP_BUNDLE" ]]; then
  FALLBACK_BUNDLE="$DIST_DIR/LarkSync/LarkSync.app"
  if [[ -d "$FALLBACK_BUNDLE" ]]; then
    APP_BUNDLE="$FALLBACK_BUNDLE"
  fi
fi

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "ERROR: .app bundle not found: $APP_BUNDLE"
  exit 1
fi

APP_VERSION="${APP_VERSION:-}"
if [[ -z "$APP_VERSION" ]]; then
  APP_VERSION="$(awk -F '"' '/^[[:space:]]*version[[:space:]]*=/ { print $2; exit }' "$ROOT_DIR/apps/backend/pyproject.toml" 2>/dev/null || true)"
  APP_VERSION="${APP_VERSION:-0.0.0}"
fi

APP_ARCH_SUFFIX="${APP_ARCH_SUFFIX:-}"
if [[ -n "$APP_ARCH_SUFFIX" ]]; then
  DMG_NAME="LarkSync-${APP_VERSION}-${APP_ARCH_SUFFIX}.dmg"
else
  DMG_NAME="LarkSync-${APP_VERSION}.dmg"
fi
OUTPUT_PATH="$DIST_DIR/$DMG_NAME"

DMG_TOOL="${LARKSYNC_DMG_TOOL:-auto}"
case "$DMG_TOOL" in
  auto)
    if command -v create-dmg >/dev/null 2>&1; then
      DMG_TOOL="create-dmg"
    else
      DMG_TOOL="hdiutil"
    fi
    ;;
  create-dmg|hdiutil)
    ;;
  *)
    echo "ERROR: unsupported LARKSYNC_DMG_TOOL: $DMG_TOOL (expected auto, create-dmg, or hdiutil)"
    exit 1
    ;;
esac

if [[ "$DMG_TOOL" == "create-dmg" ]]; then
  if ! command -v create-dmg >/dev/null 2>&1; then
    echo "ERROR: create-dmg not found. Install with: brew install create-dmg"
    exit 1
  fi
  rm -f "$OUTPUT_PATH"
  create-dmg \
    --volname "LarkSync" \
    --window-size 600 400 \
    --icon-size 100 \
    --app-drop-link 450 200 \
    --icon "LarkSync.app" 150 200 \
    "$OUTPUT_PATH" \
    "$APP_BUNDLE"
else
  if ! command -v hdiutil >/dev/null 2>&1; then
    echo "ERROR: hdiutil not found; cannot create a macOS DMG"
    exit 1
  fi

  STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/larksync-dmg.XXXXXX")"
  cleanup() {
    rm -rf "$STAGING_DIR"
  }
  trap cleanup EXIT

  rm -f "$OUTPUT_PATH"
  if command -v ditto >/dev/null 2>&1; then
    ditto "$APP_BUNDLE" "$STAGING_DIR/LarkSync.app"
  else
    cp -R "$APP_BUNDLE" "$STAGING_DIR/LarkSync.app"
  fi
  ln -s /Applications "$STAGING_DIR/Applications"

  hdiutil create \
    -volname "LarkSync" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDZO \
    "$OUTPUT_PATH"
fi

echo "OK: DMG created at $OUTPUT_PATH"
