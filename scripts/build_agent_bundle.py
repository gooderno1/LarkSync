"""Build a portable SKILL.md distribution with its stdlib CLI and checksum."""
from __future__ import annotations

import argparse
import hashlib
import re
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PROJECT_ROOT / "integrations/skills/larksync"


def build_bundle(*, output_dir: Path, version: str) -> Path:
    version = version.lstrip("v")
    if not re.fullmatch(r"[0-9A-Za-z.-]+", version):
        raise ValueError("Invalid version")
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"LarkSync-Agent-Skill-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for source in sorted(SKILL_ROOT.rglob("*")):
            if source.is_file() and source.suffix in {".md", ".py", ".yaml", ".json"}:
                z.write(source, "larksync/" + source.relative_to(SKILL_ROOT).as_posix())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument("--version")
    args = parser.parse_args()
    project = (PROJECT_ROOT / "apps/backend/pyproject.toml").read_text(encoding="utf-8")
    version = args.version or re.search(r'^version\s*=\s*"([^"]+)"', project, re.MULTILINE).group(1)
    print(build_bundle(output_dir=args.output_dir, version=version))


if __name__ == "__main__":
    main()
