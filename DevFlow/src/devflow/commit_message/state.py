from typing import TypedDict


class CommitMessageState(TypedDict, total=False):
    min_length: int
    max_length: int
    branch_name: str
    story_code: str | None
    changed_files: list[str]
    diff: str
    commit_type: str
    description: str
    message: str
    rejected_descriptions: list[str]
    feedback: str | None
    review_action: str
    copied_message: str
    llm_input_tokens: int
    llm_output_tokens: int
    llm_cost: float
    error: str | None
