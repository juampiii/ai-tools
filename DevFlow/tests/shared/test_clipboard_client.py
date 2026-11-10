import subprocess
from typing import Any

import pytest

from devflow.shared.clipboard_client import WindowsClipboardClient
from devflow.shared.errors import ClientError


class RecordingRunner:
    def __init__(self, returncode: int = 0, stderr: bytes = b"", error: Exception | None = None):
        self.returncode = returncode
        self.stderr = stderr
        self.error = error
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        self.calls.append((command, kwargs))
        if self.error:
            raise self.error
        return subprocess.CompletedProcess(command, self.returncode, stdout=b"", stderr=self.stderr)


def test_copy_pipes_the_text_to_clip_as_utf16_without_bom_and_without_shell():
    runner = RecordingRunner()

    WindowsClipboardClient(runner=runner).copy("fix: Café.")

    command, kwargs = runner.calls[0]
    assert command == ["clip"]
    assert kwargs["input"] == "fix: Café.".encode("utf-16-le")
    assert not kwargs["input"].startswith(b"\xff\xfe")
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert "shell" not in kwargs


def test_copy_raises_client_error_when_clip_fails():
    runner = RecordingRunner(returncode=1, stderr=b"access denied")

    with pytest.raises(ClientError, match="access denied"):
        WindowsClipboardClient(runner=runner).copy("text")


def test_copy_raises_client_error_when_clip_is_missing():
    runner = RecordingRunner(error=FileNotFoundError())

    with pytest.raises(ClientError, match="clip"):
        WindowsClipboardClient(runner=runner).copy("text")
