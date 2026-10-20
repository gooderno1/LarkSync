import hashlib
import importlib.util
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("build_agent_bundle", ROOT / "scripts/build_agent_bundle.py")
assert spec and spec.loader
bundle = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bundle
spec.loader.exec_module(bundle)


def test_bundle_is_self_contained_and_checksum_matches(tmp_path):
    archive = bundle.build_bundle(output_dir=tmp_path, version="0.11.0-dev.1")
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        assert "larksync/SKILL.md" in names
        assert "larksync/scripts/larksync_cli.py" in names
        assert "larksync/references/commands.md" in names
        assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
    checksum = archive.with_suffix(".zip.sha256").read_text().split()[0]
    assert checksum == hashlib.sha256(archive.read_bytes()).hexdigest()
