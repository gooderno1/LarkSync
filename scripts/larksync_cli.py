"""Compatibility entry point; the distributable Skill owns the stdlib-only CLI."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integrations.skills.larksync.scripts import larksync_cli as _impl

# Preserve imports used by existing integrations, including private helper functions.
globals().update({key: value for key, value in vars(_impl).items() if not key.startswith("__")})

if __name__ == "__main__":
    raise SystemExit(_impl.main(sys.argv[1:]))
