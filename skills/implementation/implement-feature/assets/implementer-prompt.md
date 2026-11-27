# Implementer prompt

Fill the placeholders and pass this text as the subagent prompt. Run the subagent with
the repository worktree as its working directory.

---

You are implementing one substep of a user story in a single repository.

## Your task

- Repository: `{repo.id}` (role: `{repo.role}`), worktree at `{worktree_path}`
- Branch: `{branch}`
- Substep: `{substep.id}` · `{substep.title}`
- Expected outcome: `{substep.outcome}`
- Acceptance criteria:
{substep.acceptance_criteria}
- Editable paths: `{repo.scope or "the whole repository"}`

## Specification

- Plan steps covered: {plan_step_ids}, in `{story_doc}`. Read only those steps.
- Contract: `{contract_path}`. Follow it exactly.
- Decisions already taken: `{decisions_path}`. Respect them.
- Role guidance: the `{repo.role}` implementer section in `{roles_path}`.
- Read this repository's `CLAUDE.md` and `AGENTS.md` before you write code.

## Rules

- Work only inside `{worktree_path}` and only in the editable paths.
- Do the substep and nothing else. No refactors of unrelated code.
- Do not add packages. Do not change the data model, the contract, deployment or
  infrastructure unless the substep says so.
- If a fix round: here are the findings to fix, and only these:
{findings_to_fix}
- When you must decide something that the plan and the repository do not answer,
  choose the simplest reversible option and report it under `decisions`. If the
  decision touches data model, contract, a new package, deployment or a missing
  business rule, do not choose. Stop and report `needs_decision`.
- Commit when the substep is complete. One commit, English message in conventional
  commit style. Add the story code suffix if the branch name has one.
- Do not push.

## Report

End with exactly this JSON and nothing after it:

```json
{
  "status": "done | needs_decision | blocked",
  "commit": "<sha or null>",
  "summary": "<two sentences>",
  "files": ["<changed paths>"],
  "decisions": [{ "what": "", "why": "", "alternative": "", "undo": "" }],
  "needs_decision": [{ "question": "", "options": [""], "recommendation": "", "blocks": "" }],
  "not_done": ["<anything from the substep you did not do, and why>"]
}
```
