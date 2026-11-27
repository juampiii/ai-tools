---
name: implement-feature
description: Implement an agreed user story across one or more repositories (backend, frontend, IaC) with subagents. Splits the plan into substeps, runs each substep through an implementer and an independent reviewer, escalates only the decisions that cannot be made safely, and ends with one pull request per repository for the user to review. Needs an agreed plan (see plan-feature). Use when the user asks to implement, build or deliver a story or feature from its plan. The user may write in Spanish.
---

# Implement a feature from an agreed plan

Turn an agreed plan into reviewed pull requests with as little interruption as
possible. The user takes part at the start (intake) and when a decision cannot be
made safely. At the end, the user only reviews the pull requests.

You are the orchestrator. You coordinate, decide, and talk to the user. You do not
write production code yourself. Subagents write code and review it.

## Language

Talk to the user in the language they write in. Write code, commits and PR text in
English. Write story files (`decisions.md`, reports) in the language of the story
document.

## Scope

- Input is a user story with an agreed plan. Bugs are out of scope unless the user
  says the bug is complex and asks for this flow.
- Supported repository roles: `backend`, `frontend`, `iac`. Shared libraries and test
  repositories are out of scope for now.
- IaC may live inside the backend repository. Model it as a separate role with its
  own path scope (see [the manifest](references/story-manifest.md)).
- Do not merge pull requests. Never.

## Phase 0. Preconditions

1. Find the story folder. Follow repository conventions; the default is
   `docs/stories/<identifier>/README.md`. If the user gave a path, use it.
2. Read the plan. It is ready only if its status says agreed (`Acordado` or `Agreed`)
   and its steps have observable acceptance criteria.
3. If there is no plan, or it is only proposed, stop. Tell the user that an agreed
   plan is required before implementation and that `plan-feature` creates it. Do not
   write the plan yourself and do not start any work.
4. If `implementation/state.json` exists in the story folder, this is a resume. Read
   it and continue from the recorded state instead of starting again.

## Phase 1. Intake (the user is in the loop)

Goal: take every decision that is cheap to take now and expensive later. Work through
this phase in one conversation, then do not interrupt again unless the
[escalation policy](references/escalation-policy.md) says so.

1. **Topology.** From the plan, propose the repositories involved, their roles, local
   paths, base branches, hosting (GitHub or Azure DevOps) and build/test/style
   commands. Look for the commands in each repository's `README`, `CLAUDE.md` and
   `AGENTS.md`. Ask about anything you cannot find. The user confirms the manifest.
2. **Mode.** Propose `parallel` or `sequential` (backend first):
   - `parallel` when the contract between repositories can be written now.
   - `sequential` when the domain is new and the contract will probably change after
     seeing the real model.
3. **Contract.** For `parallel`, write the contract before any implementation:
   endpoints and payloads, error codes and parameters, i18n keys when they apply.
   Save it in `implementation/contract.md` (or link an OpenAPI file). It is a
   public contract, so the user approves it here.
4. **Substeps.** Split the plan steps of each repository into substeps. A substep has
   one verifiable outcome and can be reviewed in one pass. Model, mapping and
   migration stay in one substep with one writer. Show the list to the user.
5. **Open decisions.** Collect all open decisions from the plan and from your reading
   of the code. Apply the escalation policy to each one. Ask the ones that need the
   user, in one grouped round with a recommendation per question. Record the rest in
   `decisions.md`.
6. **Permissions for the run.** Ask once, with defaults:
   - Commit on the feature branches: yes.
   - Push and open pull requests at the end: yes.
   - Run integration and end-to-end tests locally: ask per project. The user may
     allow it for small projects.
7. Save `implementation/state.json` and `implementation/decisions.md` from the
   [templates](assets/). Tell the user the run starts now.

## Phase 2. Execute (autonomous)

Create one branch and one git worktree per repository, from the base branch. Follow
the repository's branch naming. One writer per repository at any time.

For each repository, repeat for every substep:

1. **Implement.** Launch an implementer subagent with the
   [implementer prompt](assets/implementer-prompt.md). It works only in that
   repository's worktree and ends with a commit.
2. **Gate.** Run build, unit tests and the style check of the repository. If the gate
   fails because of the substep, send the failure back to the implementer. Do not
   start the review on a red gate.
3. **Review.** Launch a reviewer subagent with the
   [reviewer prompt](assets/reviewer-prompt.md). It receives the specification, the
   diff of the substep commit and the gate results. It never receives the
   implementer's reasoning or conversation. It is read-only.
4. **Verdict.** On `pass`, record it and go to the next substep. On `fail`, send the
   blocker and major findings to the implementer. Allow at most two fix rounds. If
   the substep is still failing, escalate to the user with the last report.
   Minor findings are logged and do not block.
5. **Needs decision.** If a subagent returns `needs_decision`, apply the escalation
   policy. Decide and log, or queue the question.

Subagents cannot launch other subagents, so you run the loop. In `parallel` mode,
launch the implementers of different repositories in the same message and in the
background. When one finishes, run its gate and launch its reviewer without waiting
for the other. In `sequential` mode, finish the backend repository before opening the
frontend repository, and use the real backend contract.

When a repository has no substeps left, run one full-branch review against the whole
specification of that repository. Fix blockers the same way.

**Questions.** Do not block the whole run on a queued question. Continue with work
that does not depend on it. When nothing else can move, or at the end of Phase 2, ask
the queued questions in one grouped round using `AskUserQuestion`.

**Contract changes.** If a substep needs a contract change, stop the dependent work.
This is an irreversible decision. Queue it with a recommendation and update
`implementation/contract.md` only after the user answers.

## Phase 3. Integrate

1. Check what is already running before starting anything: containers, databases,
   ports and dev servers. Reuse what matches. Never stop or remove what you did not
   start. Stop what you started when you finish.
2. If the user allowed it, run integration tests of each repository. Then run the
   end-to-end tests of the frontend against the real backend branch. If it is not
   allowed, list them as not run and say they are left to the pull request CI.
3. Fix failures caused by the change. Do not fix failures that already existed;
   report them.

## Phase 4. Deliver

1. Push each branch and open one pull request per repository, if the user allowed it.
   Use `gh` for GitHub. For Azure DevOps use `az repos pr create` if available.
   If you cannot open it, write the description to `implementation/pr-<repo>.md` and
   tell the user.
2. The description is in English and contains: what changed and why, the plan steps it
   covers, the decisions taken without the user (from `decisions.md`), verification
   evidence with what was not verified, and links to the pull requests of the other
   repositories.
3. Do not edit the agreed plan. Record deviations in `decisions.md`. Suggest running
   `plan-feature` to close the story.
4. Report to the user in a few lines: pull request links, decisions taken for them,
   open risks, and what was not run. Leave the review to the user.

## Rules for you

- A decision you take alone goes into `decisions.md` before you act on it.
- Never claim a check passed unless you saw the output.
- Do not add production dependencies, change deployment or infrastructure, change the
  data model or the public contract without the user. See the escalation policy.
- Keep the story folder as the source of truth. After every substep update
  `state.json`. A new session must be able to resume from it.
- Do not run the style or test commands of one repository in another.
- If a subagent report is vague, ask it for evidence. Do not infer it.
