import subprocess
from pathlib import Path
from typing import Any

import pytest

from devflow.shared.errors import ClientError
from devflow.shared.git_client import FileChange, SubprocessGitClient


class RecordingRunner:
    def __init__(
        self,
        returncode: int = 0,
        stderr: str = "",
        error: Exception | None = None,
        stdout: str = "",
    ):
        self.returncode = returncode
        self.stderr = stderr
        self.error = error
        self.stdout = stdout
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, kwargs))
        if self.error:
            raise self.error
        return subprocess.CompletedProcess(
            command, self.returncode, stdout=self.stdout, stderr=self.stderr
        )


def test_fetch_runs_git_fetch_with_remote_and_branch():
    runner = RecordingRunner()

    SubprocessGitClient(runner=runner).fetch("origin", "develop")

    assert runner.calls[0][0] == ["git", "fetch", "origin", "develop"]


def test_create_branch_runs_git_checkout_with_start_point():
    runner = RecordingRunner()

    SubprocessGitClient(runner=runner).create_branch("feature/1-x", "origin/develop")

    assert runner.calls[0][0] == ["git", "checkout", "-b", "feature/1-x", "origin/develop"]


def test_get_remote_url_runs_git_remote_get_url_and_returns_the_trimmed_output():
    runner = RecordingRunner(stdout="https://github.com/acme/repo.git\n")

    url = SubprocessGitClient(runner=runner).get_remote_url("origin")

    assert runner.calls[0][0] == ["git", "remote", "get-url", "origin"]
    assert url == "https://github.com/acme/repo.git"


def test_get_remote_url_raises_client_error_when_the_remote_does_not_exist():
    runner = RecordingRunner(returncode=2, stderr="error: No such remote 'origin'")

    with pytest.raises(ClientError, match="No such remote"):
        SubprocessGitClient(runner=runner).get_remote_url("origin")


def test_commands_run_without_shell_and_capture_output(tmp_path: Path):
    runner = RecordingRunner()

    SubprocessGitClient(cwd=tmp_path, runner=runner).fetch("origin", "develop")

    kwargs = runner.calls[0][1]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert "shell" not in kwargs


def test_non_zero_exit_code_raises_client_error_with_stderr():
    runner = RecordingRunner(returncode=128, stderr="fatal: not a git repository")

    with pytest.raises(ClientError, match="not a git repository"):
        SubprocessGitClient(runner=runner).fetch("origin", "develop")


def test_missing_git_executable_raises_client_error():
    runner = RecordingRunner(error=FileNotFoundError())

    with pytest.raises(ClientError, match="git"):
        SubprocessGitClient(runner=runner).fetch("origin", "develop")


def test_get_current_branch_runs_git_branch_show_current_and_returns_the_trimmed_output():
    runner = RecordingRunner(stdout="feature/52691-x\n")

    branch = SubprocessGitClient(runner=runner).get_current_branch()

    assert runner.calls[0][0] == ["git", "branch", "--show-current"]
    assert branch == "feature/52691-x"


def test_get_current_branch_returns_an_empty_string_on_a_detached_head():
    runner = RecordingRunner(stdout="\n")

    assert SubprocessGitClient(runner=runner).get_current_branch() == ""


def test_get_changes_runs_git_status_porcelain_with_untracked_files():
    runner = RecordingRunner()

    SubprocessGitClient(runner=runner).get_changes()

    assert runner.calls[0][0] == [
        "git",
        "status",
        "--porcelain",
        "-z",
        "--untracked-files=all",
    ]


def test_get_changes_parses_modified_staged_untracked_and_deleted_files():
    output = " M src/app.py\0A  src/new.py\0?? docs/notes.md\0 D old.py\0MM both.py\0"
    runner = RecordingRunner(stdout=output)

    changes = SubprocessGitClient(runner=runner).get_changes()

    assert changes == [
        FileChange("src/app.py", "M"),
        FileChange("src/new.py", "A"),
        FileChange("docs/notes.md", "??"),
        FileChange("old.py", "D"),
        FileChange("both.py", "MM"),
    ]


def test_get_changes_skips_the_original_path_of_a_rename():
    runner = RecordingRunner(stdout="R  new name.py\0old name.py\0 M other.py\0")

    changes = SubprocessGitClient(runner=runner).get_changes()

    assert changes == [FileChange("new name.py", "R"), FileChange("other.py", "M")]


def test_get_changes_returns_an_empty_list_when_the_tree_is_clean():
    assert SubprocessGitClient(runner=RecordingRunner(stdout="")).get_changes() == []


def test_get_diff_runs_git_diff_head_limited_to_the_given_paths():
    runner = RecordingRunner(stdout="the diff")

    diff = SubprocessGitClient(runner=runner).get_diff(["src/a.py", "src/b.py"])

    assert runner.calls[0][0] == ["git", "diff", "HEAD", "--", "src/a.py", "src/b.py"]
    assert diff == "the diff"
