from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(ROOT))

from scripts import configure_macos_release_secrets as configure  # noqa: E402


def test_required_secrets_cover_signing_and_notarization() -> None:
    assert configure.REQUIRED_SECRETS == (
        "MACOS_CERTIFICATE_P12_BASE64",
        "MACOS_CERTIFICATE_PASSWORD",
        "MACOS_CODESIGN_IDENTITY",
        "APPLE_ID",
        "APPLE_TEAM_ID",
        "APPLE_APP_SPECIFIC_PASSWORD",
    )


def test_encode_certificate_returns_single_line_base64(tmp_path: Path) -> None:
    certificate = tmp_path / "developer-id.p12"
    certificate.write_bytes(b"private-certificate-bytes")

    encoded = configure.encode_certificate(certificate)

    assert encoded == base64.b64encode(certificate.read_bytes()).decode("ascii")
    assert "\n" not in encoded


def test_set_repository_secret_uses_stdin_instead_of_command_arguments() -> None:
    calls: list[tuple[list[str], str]] = []

    def fake_run(command: list[str], *, input_text: str = "") -> subprocess.CompletedProcess[str]:
        calls.append((command, input_text))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    configure.set_repository_secret(
        "gooderno1/LarkSync",
        "APPLE_APP_SPECIFIC_PASSWORD",
        "secret-value",
        runner=fake_run,
    )

    assert calls == [
        (
            [
                "gh",
                "secret",
                "set",
                "APPLE_APP_SPECIFIC_PASSWORD",
                "--repo",
                "gooderno1/LarkSync",
            ],
            "secret-value",
        )
    ]
    assert "secret-value" not in calls[0][0]


def test_missing_required_secrets_is_ordered() -> None:
    existing = {"APPLE_ID", "APPLE_TEAM_ID"}

    assert configure.missing_required_secrets(existing) == [
        "MACOS_CERTIFICATE_P12_BASE64",
        "MACOS_CERTIFICATE_PASSWORD",
        "MACOS_CODESIGN_IDENTITY",
        "APPLE_APP_SPECIFIC_PASSWORD",
    ]

