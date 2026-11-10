from typing import TypedDict


class StartBranchState(TypedDict, total=False):
    card_id: int
    card_title: str
    card_type: str
    branch_prefix: str
    branch_name: str
    branch_slug: str
    rejected_slugs: list[str]
    feedback: str | None
    review_action: str
    created_branch: str
    llm_input_tokens: int
    llm_output_tokens: int
    llm_cost: float
    error: str | None
