import subprocess
from collections.abc import Callable
from typing import Protocol

from devflow.shared.errors import ClientError


class ClipboardClient(Protocol):
    def copy(self, text: str) -> None: ...


class WindowsClipboardClient:
    """Clipboard client that pipes the text to `clip.exe` (Windows only)."""

    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    ) -> None:
        self._runner = runner

    def copy(self, text: str) -> None:
        # clip.exe reads UTF-16 LE, so non-ASCII characters are kept.
        # No BOM: clip would copy it as a visible character.
        try:
            result = self._runner(
                ["clip"], input=text.encode("utf-16-le"), check=False, capture_output=True
            )
        except FileNotFoundError as exc:
            raise ClientError("The clip executable was not found in PATH.") from exc

        if result.returncode != 0:
            detail = result.stderr.decode(errors="replace").strip() or "no detail"
            raise ClientError(f"`clip` failed: {detail}")
