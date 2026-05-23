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


def test_release_workflow_cancels_stale_runs_for_same_pr() -> None:
    workflow = _load_release_workflow()

    concurrency = workflow["concurrency"]

    assert concurrency["cancel-in-progress"] is True
    assert concurrency["group"] == "release-build-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}"


def test_release_workflow_uses_native_dual_arch_macos_matrix() -> None:
    workflow = _load_release_workflow()

    expected = [
        {"os": "macos-15-intel", "arch": "x86_64"},
        {"os": "macos-14", "arch": "arm64"},
    ]
    quality_matrix = workflow["jobs"]["quality-macos-packaging"]["strategy"]["matrix"]["include"]
    quality_fail_fast = workflow["jobs"]["quality-macos-packaging"]["strategy"]["fail-fast"]
    release_matrix = workflow["jobs"]["build-macos"]["strategy"]["matrix"]["include"]
    release_fail_fast = workflow["jobs"]["build-macos"]["strategy"]["fail-fast"]
    quality_smoke_env = _step(
        workflow,
        "quality-macos-packaging",
        "Build macOS installer smoke",
    )["env"]
    release_build_env = _step(workflow, "build-macos", "Build DMG")["env"]
    quality_install_smoke = _step(
        workflow,
        "quality-macos-packaging",
        "Run macOS install-launch smoke",
    )["run"]
    release_install_smoke = _step(workflow, "build-macos", "Run macOS install-launch smoke")["run"]

    assert quality_matrix == expected
    assert release_matrix == expected
    assert quality_fail_fast is False
    assert release_fail_fast is False
    assert quality_smoke_env["LARKSYNC_MACOS_TARGET_ARCH"] == "${{ matrix.arch }}"
    assert quality_smoke_env["LARKSYNC_MACOS_DMG_SUFFIX"] == "${{ matrix.arch }}"
    assert release_build_env["LARKSYNC_MACOS_TARGET_ARCH"] == "${{ matrix.arch }}"
    assert release_build_env["LARKSYNC_MACOS_DMG_SUFFIX"] == "${{ matrix.arch }}"
    assert quality_install_smoke == "python scripts/macos_installer_smoke.py --arch-suffix ${{ matrix.arch }}"
    assert release_install_smoke == "python scripts/macos_installer_smoke.py --arch-suffix ${{ matrix.arch }}"
