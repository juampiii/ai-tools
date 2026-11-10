import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from devflow.shared.errors import ClientError


@dataclass(frozen=True)
class FileChange:
    path: str
    status: str  # git status code without padding, for example "M", "A", "D" or "??"


class GitClient(Protocol):
    def fetch(self, remote: str, branch: str) -> None: ...

    def create_branch(self, name: str, start_point: str) -> None: ...

    def get_remote_url(self, remote: str) -> str: ...

    def get_current_branch(self) -> str: ...

    def get_changes(self) -> list[FileChange]: ...

    def get_diff(self, paths: list[str]) -> str: ...


class SubprocessGitClient:
    """Git client that runs the `git` binary on the repository in `cwd`."""

    def __init__(
        self,
        cwd: Path | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._cwd = cwd
        self._runner = runner

    def fetch(self, remote: str, branch: str) -> None:
        self._run(["fetch", remote, branch])

    def create_branch(self, name: str, start_point: str) -> None:
        self._run(["checkout", "-b", name, start_point])

    def get_remote_url(self, remote: str) -> str:
        return self._run(["remote", "get-url", remote]).strip()

    def get_current_branch(self) -> str:
        """Returns the current branch name, or an empty string on a detached HEAD."""
        return self._run(["branch", "--show-current"]).strip()

    def get_changes(self) -> list[FileChange]:
        """Returns every pending file: staged, unstaged and untracked."""
        output = self._run(["status", "--porcelain", "-z", "--untracked-files=all"])
        return _parse_status(output)

    def get_diff(self, paths: list[str]) -> str:
        """Returns the staged and unstaged diff against HEAD for the given paths."""
        return self._run(["diff", "HEAD", "--", *paths])

    def _run(self, args: list[str]) -> str:
        command = ["git", *args]
        try:
            result = self._runner(
                command, cwd=self._cwd, check=False, capture_output=True, text=True
            )
        except FileNotFoundError as exc:
            raise ClientError("The git executable was not found in PATH.") from exc

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "no detail"
            raise ClientError(f"`{' '.join(command)}` failed: {detail}")

        return result.stdout


def _parse_status(output: str) -> list[FileChange]:
    """Parses `git status --porcelain -z`: entries are `XY path`, renames add the old path."""
    entries = output.split("\0")
    changes: list[FileChange] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue

        status, path = entry[:2], entry[3:]
        if "R" in status or "C" in status:
            index += 1  # skip the original path of the rename or copy
        changes.append(FileChange(path=path, status=status.strip()))
    return changes
