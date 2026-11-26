---
name: plan-feature
description: Agree on a readable feature implementation plan through conversation, orient the user during implementation, and document the outcome while preserving the original plan. Use when preparing or closing stories, or reconstructing their decisions retrospectively. The workflow and template are reusable across projects.
---

# Plan a feature and document its delivery

The document helps the user understand the work and, months later, recall what was
decided, why, and what was done. Write for that person and adapt explanations to
their knowledge. Use the document language requested by the user or established by
the project; otherwise use the user's language. The supplied template and example
are in Spanish. Adapt their language when needed; English skill instructions do
not require English output.

## Location and resources

- Follow repository conventions. By default, use
  `docs/issues/<identifier>/README.md` from the repository root. If there is no
  identifier, agree on a name before creating a permanent folder; do not invent numbers.
- Read [the template](assets/issue-plan.md) to build the document.
  Adapt the number of steps and omit optional sections that add no value.
- Consult [the fictional example](references/completed-example.md) when you need
  a sample of the expected detail or how to explain deviations.
- Keep the skill portable: do not assume an issue provider, programming language,
  infrastructure, or execution tool. Links and paths in the generated document
  must work from its destination location.

## 1. Define the plan through conversation

1. Read the issue and its document when available, local instructions, and relevant
   files. Reuse decisions already agreed on in the conversation.
2. Clarify the problem, desired outcome, scope, and decisions that affect the approach.
   Present options and their rationale when a meaningful choice exists. Group pending
   questions; avoid asking about details you can infer.
3. Propose an overview of steps with observable outcomes. Explain the technical
   concepts the user needs to assess the proposal.
4. Agree on the approach before implementing. If already agreed, proceed without
   asking for confirmation again. Creating the document does not authorize additional
   external actions.
5. Save the plan using the template and record the agreement date. Identify proposals
   that are not yet agreed as such. Leave the closing section pending.

Use two short paragraphs for the objective: problem and outcome; scope and expected
experience. Preserve important decisions and their rationale, including rejected
alternatives. Identify unresolved questions and the steps that depend on them.

Use matching identifiers and names in the table, diagram, and step descriptions.
Mermaid arrows represent dependencies; branches can progress in parallel only when
they do not depend on each other. Drawing parallel branches does not itself authorize
delegation or parallel execution.

### Define concrete steps

- Name each step with an action and its specific object or capability. Include the
  destination or system when it distinguishes the outcome. For example, use
  "Build and publish the API and migration images to GHCR" rather than
  "Prepare tests and publishing".
- Make the title understandable from the overview alone. Avoid interchangeable
  headings such as "Prepare the environment", "Connect the pieces", or "Validate
  everything" when the actual resource, connection, or behavior is known.
- Derive the step from its deliverable: what artifact will exist, what capability
  will work, or what uncertainty will be resolved? Name the principal outcome;
  keep prerequisites and supporting tasks inside the step. Tests required before
  image publication should not obscure the goal of making both images available.
- Use the overview columns for different purposes: the title identifies the action,
  "What we will do" describes the work, and "Expected outcome" states the observable
  end state. Acceptance criteria must demonstrate that end state rather than merely
  say that configuration or implementation is complete.
- Keep steps at a useful scale for the user: split independently verifiable outcomes
  when they have distinct dependencies; keep commands and routine subtasks in the
  description. Precision does not require one step per file or command.
- Be specific only where supported by the issue, repository, or agreed decisions.
  Mark unknown targets as unresolved and identify what will determine them; do not
  invent tools or architecture to make a title sound concrete.

## 2. Guide the user during implementation

- Before a phase, identify the corresponding step and explain its intended outcome.
  In progress updates, explain what was learned and what remains unresolved.
- Keep the agreed plan stable during implementation. Do not turn it into a command
  log or continually update every subtask in the document.
- When a significant deviation in scope, solution, or risk arises, explain its impact
  and agree on the change before executing dependent work. Routine choices within
  the agreed approach do not require new approval.
- When another agent resumes the story, read the document and compare it with the
  available code, PR, and evidence. The plan records intent; it does not prove which
  tasks were executed. Do not assume results or repeat sensitive operations.
- If the user explicitly requests a plan revision during the story, preserve an
  identified copy of the original version and date the revision; do not silently
  replace it.

## 3. Close or reconstruct the story

At the end, review the document once against the actual outcome. Preserve the original
plan and complete the closing section, validation, outstanding work, and technical
reference. If required work remains, describe the outcome as partial rather than closed.

Map deviations to the original steps and explain their reasons. Distinguish verified
results, user-reported results, and unverified items. Link relevant evidence and do
not invent runs, decisions, or dates.

For retrospective analysis, state that the plan was reconstructed after the work and
integrate the relevant facts into a self-contained account. Separate known initial
decisions from later discoveries; express any uncertainty. Prefer durable references
such as issues, PRs, commits, files, and validation procedures. Do not narrate how
information reached the agent through chats, screenshots, or another session unless
the user explicitly asks for an evidence audit. Preserve verification limits by
describing what was and was not checked, rather than requiring readers to consult a chat.

The final reference should help locate files, configuration, logs, and operational
guides. Document secret names and purposes, never their values. Keep current operating
instructions in their dedicated guide and link to it to avoid duplication.

## Document review

Check that the user can explain the objective, step order, rationale for decisions,
and how the outcome will be demonstrated. Check that dependencies and identifiers
match and every step has an outcome and observable acceptance criteria. At closure,
ensure the changes can be understood without consulting the chat history.
Read the overview on its own: can the user tell what each step produces and where,
without opening its description? Replace generic titles and check that the principal
outcome matches the title, diagram, description, and acceptance criteria.
