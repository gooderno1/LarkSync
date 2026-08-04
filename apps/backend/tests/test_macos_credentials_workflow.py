from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_FILE = PROJECT_ROOT / ".github" / "workflows" / "macos-release-credentials.yml"


def test_macos_credentials_workflow_is_manual_and_read_only() -> None:
    raw = WORKFLOW_FILE.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in raw
    assert "push:" not in raw
    assert "pull_request:" not in raw
    assert "contents: read" in raw


def test_macos_credentials_workflow_validates_certificate_and_notary_account() -> None:
    workflow = yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))
    job = workflow["jobs"]["validate-macos-release-credentials"]
    steps = {step["name"]: step for step in job["steps"]}

    assert job["runs-on"] == "macos-14"
    assert set(steps["Check required secrets"]["env"]) == {
        "MACOS_CERTIFICATE_P12_BASE64",
        "MACOS_CERTIFICATE_PASSWORD",
        "MACOS_CODESIGN_IDENTITY",
        "APPLE_ID",
        "APPLE_TEAM_ID",
        "APPLE_APP_SPECIFIC_PASSWORD",
    }

    certificate_check = steps["Import and validate Developer ID certificate"]["run"]
    assert "base64 -D" in certificate_check
    assert "security import" in certificate_check
    assert "security find-identity" in certificate_check
    assert "codesign --verify --strict" in certificate_check

    notary_check = steps["Validate Apple notarization credentials"]["run"]
    assert "xcrun notarytool history" in notary_check
    assert '--apple-id "$APPLE_ID"' in notary_check
    assert '--team-id "$APPLE_TEAM_ID"' in notary_check
    assert '--password "$APPLE_APP_SPECIFIC_PASSWORD"' in notary_check
