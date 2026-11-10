import pytest

from devflow.commit_message.nodes import (
    COMPLEXITY,
    MAX_DIFF_LENGTH,
    MESSAGE_JSON_SCHEMA,
    compose_message,
    extract_story_code,
    is_lock_file,
    is_noise,
    make_copy_message,
    make_propose_message,
    make_read_branch,
    make_read_changes,
    normalize_description,
    select_relevant_changes,
    truncate_diff,
)
from devflow.shared.git_client import FileChange
from tests.fakes import FakeClipboardClient, FakeGitClient, FakeLlmClient, message_json

# --- extract_story_code ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("branch", "expected"),
    [
        ("feature/52691-some-name", "52691"),
        ("bugfix/52691-some-name", "52691"),
        ("feature/52691", "52691"),
        ("main", None),
        ("develop", None),
        ("hotfix/quick-patch", None),
        ("feature/1234-short", None),
        ("feature/123456-too-long", None),
        ("52691-no-prefix", None),
        ("", None),
    ],
)
def test_extract_story_code_reads_the_five_digits_after_the_prefix(branch, expected):
    assert extract_story_code(branch) == expected


# --- noise filter ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        ".gitignore",
        ".claude/settings.json",
        "src/.hidden/file.py",
        "bin/Debug/app.dll",
        "src/Api/obj/project.assets.json",
        "node_modules/lib/index.js",
        "git-changes-summary.md",
        "docs/git-changes-summary-2.txt",
        "src/__pycache__/mod.cpython-312.pyc",
        "notes.tmp",
    ],
)
def test_is_noise_detects_irrelevant_files(path):
    assert is_noise(path)


@pytest.mark.parametrize(
    "path", ["src/app.py", "src/Api/Controllers/ProductController.cs", "README.md"]
)
def test_is_noise_keeps_real_source_files(path):
    assert not is_noise(path)


@pytest.mark.parametrize(
    "path", ["package-lock.json", "web/pnpm-lock.yaml", "uv.lock", "packages.lock.json"]
)
def test_is_lock_file_detects_lock_files(path):
    assert is_lock_file(path)


def test_is_lock_file_ignores_regular_files():
    assert not is_lock_file("src/app.py")


def test_select_relevant_changes_drops_noise_and_lock_files():
    changes = [
        FileChange("src/app.py", "M"),
        FileChange(".claude/notes.md", "??"),
        FileChange("uv.lock", "M"),
        FileChange("bin/app.dll", "M"),
    ]

    assert select_relevant_changes(changes) == [FileChange("src/app.py", "M")]


def test_select_relevant_changes_keeps_lock_files_when_they_are_the_only_change():
    changes = [FileChange("uv.lock", "M"), FileChange(".gitignore", "M")]

    assert select_relevant_changes(changes) == [FileChange("uv.lock", "M")]


def test_select_relevant_changes_returns_empty_when_everything_is_noise():
    assert select_relevant_changes([FileChange(".gitignore", "M")]) == []


# --- text helpers ---------------------------------------------------------------------------


def test_truncate_diff_keeps_a_short_diff_untouched():
    assert truncate_diff("short diff") == "short diff"


def test_truncate_diff_cuts_a_long_diff_and_marks_it():
    result = truncate_diff("x" * (MAX_DIFF_LENGTH + 10))

    assert result.startswith("x" * MAX_DIFF_LENGTH)
    assert result.endswith("[diff truncated]")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("add export endpoint", "Add export endpoint."),
        ("Add export endpoint.", "Add export endpoint."),
        ("  add   export\nendpoint...  ", "Add export endpoint."),
        ("", ""),
        ("...", ""),
    ],
)
def test_normalize_description_gives_one_line_with_capital_and_period(raw, expected):
    assert normalize_description(raw) == expected


def test_compose_message_appends_the_story_code():
    assert compose_message("fix", "Prevent it.", "52691") == "fix: Prevent it. story: #52691"


def test_compose_message_omits_the_suffix_without_story_code():
    assert compose_message("docs", "Update the README.", None) == "docs: Update the README."


# --- read_branch ----------------------------------------------------------------------------


def test_read_branch_returns_the_branch_and_its_story_code():
    git = FakeGitClient(branch="feature/52691-elearning-costs")

    result = make_read_branch(git)({})

    assert result == {"branch_name": "feature/52691-elearning-costs", "story_code": "52691"}


def test_read_branch_has_no_story_code_on_main():
    result = make_read_branch(FakeGitClient(branch="main"))({})

    assert result == {"branch_name": "main", "story_code": None}


def test_read_branch_returns_error_when_git_fails():
    git = FakeGitClient(branch_error="fatal: not a git repository")

    assert make_read_branch(git)({}) == {"error": "fatal: not a git repository"}


# --- read_changes ---------------------------------------------------------------------------


def test_read_changes_returns_files_with_status_and_the_diff():
    git = FakeGitClient(
        changes=[FileChange("src/app.py", "M"), FileChange("src/new.py", "??")], diff="the diff"
    )

    result = make_read_changes(git)({})

    assert result == {"changed_files": ["M src/app.py", "?? src/new.py"], "diff": "the diff"}


def test_read_changes_asks_for_the_diff_of_the_relevant_files_only():
    git = FakeGitClient(
        changes=[
            FileChange("src/app.py", "M"),
            FileChange(".gitignore", "M"),
            FileChange("uv.lock", "M"),
        ]
    )

    make_read_changes(git)({})

    assert git.diff_calls == [["src/app.py"]]


def test_read_changes_returns_error_when_there_is_nothing_meaningful():
    git = FakeGitClient(changes=[FileChange(".gitignore", "M")])

    result = make_read_changes(git)({})

    assert "no meaningful pending changes" in result["error"]
    assert git.diff_calls == []


def test_read_changes_returns_error_when_git_status_fails():
    git = FakeGitClient(changes_error="fatal: not a git repository")

    assert make_read_changes(git)({}) == {"error": "fatal: not a git repository"}


def test_read_changes_returns_error_when_git_diff_fails():
    git = FakeGitClient(diff_error="fatal: bad revision 'HEAD'")

    assert "bad revision" in make_read_changes(git)({})["error"]


# --- propose_message ------------------------------------------------------------------------


def propose_state(**overrides):
    state = {
        "changed_files": ["M src/app.py"],
        "diff": "the diff",
        "min_length": 50,
        "max_length": 70,
        "story_code": "52691",
    }
    return {**state, **overrides}


def test_propose_message_builds_the_message_with_type_description_and_story_code():
    llm = FakeLlmClient([message_json("fix", "prevent costs validation")])

    result = make_propose_message(llm)(propose_state())

    assert result["message"] == "fix: Prevent costs validation. story: #52691"
    assert result["commit_type"] == "fix"
    assert result["description"] == "Prevent costs validation."


def test_propose_message_omits_the_suffix_without_story_code():
    llm = FakeLlmClient([message_json("docs", "Update the README.")])

    result = make_propose_message(llm)(propose_state(story_code=None))

    assert result["message"] == "docs: Update the README."


def test_propose_message_sets_the_story_code_from_the_state_not_from_the_llm():
    llm = FakeLlmClient([message_json("feat", "Add it. story: #99999")])

    result = make_propose_message(llm)(propose_state())

    assert result["message"].endswith(" story: #52691")


def test_propose_message_normalizes_the_commit_type():
    llm = FakeLlmClient([message_json("  Feat ", "Add it")])

    assert make_propose_message(llm)(propose_state())["commit_type"] == "feat"


def test_propose_message_prompt_includes_files_diff_and_length_range():
    llm = FakeLlmClient([message_json("fix", "Do it")])

    make_propose_message(llm)(propose_state(min_length=80, max_length=100))

    prompt, complexity, schema = llm.calls[0]
    assert "M src/app.py" in prompt
    assert "the diff" in prompt
    assert "80 to 100 characters" in prompt
    assert complexity == COMPLEXITY
    assert schema == MESSAGE_JSON_SCHEMA


def test_propose_message_prompt_skips_the_diff_section_when_there_is_no_diff():
    llm = FakeLlmClient([message_json("fix", "Do it")])

    make_propose_message(llm)(propose_state(diff=""))

    assert "Diff of the tracked files" not in llm.calls[0][0]


def test_propose_message_prompt_includes_feedback_and_rejected_descriptions():
    llm = FakeLlmClient([message_json("fix", "Do it")])

    make_propose_message(llm)(
        propose_state(feedback="mention the endpoint", rejected_descriptions=["Change stuff."])
    )

    prompt = llm.calls[0][0]
    assert "mention the endpoint" in prompt
    assert "- Change stuff." in prompt


def test_propose_message_accumulates_the_llm_usage():
    llm = FakeLlmClient([message_json("fix", "Do it")], input_tokens=10, output_tokens=5, cost=0.01)

    result = make_propose_message(llm)(
        propose_state(llm_input_tokens=100, llm_output_tokens=50, llm_cost=0.5)
    )

    assert result["llm_input_tokens"] == 110
    assert result["llm_output_tokens"] == 55
    assert result["llm_cost"] == pytest.approx(0.51)


def test_propose_message_returns_error_when_the_llm_fails():
    llm = FakeLlmClient(error="The LLM CLI failed (502): boom")

    result = make_propose_message(llm)(propose_state())

    assert result == {"error": "The LLM CLI failed (502): boom"}


@pytest.mark.parametrize("response", ["not json", "{}", '{"type": "fix"}', "[]", "null"])
def test_propose_message_returns_error_when_the_response_is_malformed(response):
    result = make_propose_message(FakeLlmClient([response]))(propose_state())

    assert "valid commit message" in result["error"]


def test_propose_message_returns_error_for_an_unknown_type():
    llm = FakeLlmClient([message_json("wip", "Do things")])

    assert "'wip'" in make_propose_message(llm)(propose_state())["error"]


def test_propose_message_returns_error_for_an_empty_description():
    llm = FakeLlmClient([message_json("fix", "  ...  ")])

    assert "empty description" in make_propose_message(llm)(propose_state())["error"]


# --- copy_message ---------------------------------------------------------------------------


def test_copy_message_copies_the_message_to_the_clipboard():
    clipboard = FakeClipboardClient()

    result = make_copy_message(clipboard)({"message": "fix: Do it."})

    assert result == {"copied_message": "fix: Do it."}
    assert clipboard.copied == ["fix: Do it."]


def test_copy_message_returns_error_with_the_message_when_the_clipboard_fails():
    clipboard = FakeClipboardClient(error="`clip` failed: no detail")

    result = make_copy_message(clipboard)({"message": "fix: Do it."})

    assert "`clip` failed" in result["error"]
    assert "fix: Do it." in result["error"]
