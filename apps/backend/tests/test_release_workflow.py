from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_FILE = PROJECT_ROOT / ".github" / "workflows" / "release-build.yml"


def _load_release_workflow() -> dict:
    return yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))


def _step_run(workflow: dict, job_name: str, step_name: str) -> str:
    for step in workflow["jobs"][job_name]["steps"]:
        if step.get("name") == step_name:
            return step["run"]
    raise AssertionError(f"missing step {job_name}.{step_name}")


def _step(workflow: dict, job_name: str, step_name: str) -> dict:
    for step in workflow["jobs"][job_name]["steps"]:
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"missing step {job_name}.{step_name}")


def test_quality_macos_packaging_reuses_pytest_bootstrap() -> None:
    workflow = _load_release_workflow()

    windows_install = _step_run(workflow, "quality", "Install Python dependencies")
    macos_install = _step_run(
        workflow,
        "quality-macos-packaging",
        "Install Python dependencies",
    )

    assert macos_install.strip() == windows_install.strip()
    assert '"pytest>=7.4"' in macos_install
    assert '"pytest-asyncio>=0.23"' in macos_install


def test_release_workflow_uses_native_dual_arch_macos_matrix() -> None:
    workflow = _load_release_workflow()

    expected = [
        {"os": "macos-13", "arch": "x86_64"},
        {"os": "macos-14", "arch": "arm64"},
    ]
    quality_matrix = workflow["jobs"]["quality-macos-packaging"]["strategy"]["matrix"]["include"]
    release_matrix = workflow["jobs"]["build-macos"]["strategy"]["matrix"]["include"]
    quality_smoke_env = _step(
        workflow,
        "quality-macos-packaging",
        "Build macOS installer smoke",
    )["env"]
    release_build_env = _step(workflow, "build-macos", "Build DMG")["env"]

    assert quality_matrix == expected
    assert release_matrix == expected
    assert quality_smoke_env["LARKSYNC_MACOS_TARGET_ARCH"] == "${{ matrix.arch }}"
    assert quality_smoke_env["LARKSYNC_MACOS_DMG_SUFFIX"] == "${{ matrix.arch }}"
    assert release_build_env["LARKSYNC_MACOS_TARGET_ARCH"] == "${{ matrix.arch }}"
    assert release_build_env["LARKSYNC_MACOS_DMG_SUFFIX"] == "${{ matrix.arch }}"
