---
name: refine-feature
description: Refine a feature idea ("I want to be able to create a recipe...") into a user story that is ready for development, by asking business questions. Resumes an existing story document, saves the refinement and delivers Markdown to paste into an issue manually. Does not design or implement the technical solution. Use when the user wants to define, refine or create a feature, user story, PBI or ticket. The user may write in Spanish.
---

# Refine a feature into a user story

Turn a feature idea or loose notes into a clear story that can be checked from the
business side and is ready for the technical planning that follows. Aim for one
story per feature. Act as a Product Owner: never invent what is missing, ask for it.

## Language

These instructions are in English. Talk to the user in the language they
write in. Write the story in English unless the user asks for another language, and
do not ask which language to use. Translate the template headings and status values
into the language of the story. When you
resume a document, keep its language unless the user asks to change it, and
recognize its status values in either language. To get a story in another language,
save a translation as a new file instead of replacing the original (see Where to save).

## Limits

- Use only what the user provides and the document being resumed. Do not infer
  business rules from code, repository documentation, other stories, issues, a wiki
  or external sources. You can locate `docs/stories/`, list its folders and read the
  selected document.
- Nothing technical: no endpoints, entities, database, architecture or estimates.
  That belongs to the technical planning.
- Do not create issues or publish to GitHub Projects, Azure DevOps or other
  services. Publishing is manual.
- Do not call a story ready while it has blocking business decisions that are not
  confirmed.

## Where to save

- In `docs/stories/`, from the Git root even if the session starts in
  `Happymeal-BE`. If you cannot find the root, ask. Create the folder if it is missing.
- Each story has its own folder, `docs/stories/<name>/`, with one file per language,
  `<name>.<lang>.md`, for example `publish-recipe/publish-recipe.es.md`. `<lang>` is the
  two-letter language code. The progress of the story is the `**Status:**` field of
  each file.
- The name is short, lowercase, in English even when the story is written in another
  language, without accents and with hyphens. Do not invent issue numbers.
- Save the story in the language it is written. Create a file in another language only
  when the user asks. It is a translation of the same story, with the same status.
  When you change a story that has other language files, tell the user that they are
  out of date. Do not translate them unless the user asks.
- Link other stories with a relative path to the same language, for example
  `../create-recipe/create-recipe.es.md`.
- Before creating a new folder, check that the name is free. If it exists and is
  another story, use a different name. Do not overwrite a story you are not resuming.
- If writing fails, do not say you saved it. Keep the content in the chat and explain
  what is missing to save it.

## Phase 1: Refine

1. **Start.** If the user names a document, read it. If not, list the story folders
   and judge from their names only whether one is related. Do not open a story to
   decide that. If one may be related, or several, ask which one to resume or whether
   this is a new story. Read a story only when the user selects it, and never use
   another story's content to ask questions or propose rules. If the selected story has
   several language files, read the one in the language the user writes or asks for.
2. **Summary.** Explain in two or three sentences what you understood. When resuming,
   recall the confirmed decisions, the pending proposals and the open questions.
3. **Round of questions.** Ask up to five questions, only the necessary ones, ordered
   by impact. Cover role, capability, benefit, scope and business rules. Also cover
   the happy path, errors and edge cases when they apply, without inventing
   scenarios. Do not repeat decisions that are already resolved.
4. **Proposals.** When there is enough basis, add a proposed answer to each question,
   marked **pending confirmation**, so the user can reply "ok". If there is no basis,
   ask without inventing. Never present a proposal or an example as a rule.
5. **What each reply confirms.** An "ok" (or its equivalent in the user's language)
   confirms only the explicit proposals of the current round. A partial reply
   confirms only what it answers and the rest stays pending. An order to stop
   confirms nothing.
6. **Contradictions.** If a reply contradicts a previous decision and does not clearly
   ask for a change, ask which one wins. Until then, it is a blocking question and
   you do not replace the earlier decision.
7. **Save.** Write the document after the first round and update it after each
   round, before waiting for the reply. Keep confirmed decisions, pending proposals
   and open questions apart, and mark which ones block. Identify the proposals of the
   current round so an "ok" can be read when the story is resumed. Remove what was
   discarded and check that rules and criteria reflect the same decisions.
8. **Size.** Aim for one story. If the feature is too big for one, propose
   deliveries with independent value and ask the user to confirm the split before
   going on. Refine the confirmed stories one at a time, each in its own folder. Do not
   create a story the user has not confirmed. Keep what is confirmed in common and
   the questions of each story.
9. **Repeat** until the checklist is met or the user wants to stop.

## Checklist: ready for technical planning

- The role that benefits, the capability and the business value are clear.
- The business rules are defined and confirmed.
- There are criteria for the happy path, errors and edge cases that apply.
- Each criterion describes an observable result and does not impose how it is built.
- What is out of scope is explicit.
- No blocking business decision is left. A question or proposal is blocking if it
  could change who can do what, the benefit, the scope, the rules or the acceptable
  result. A purely technical question is noted as non-blocking and solved during
  planning.
- INVEST as a guide, without replacing the team's judgment: independent, negotiable,
  valuable, estimable (there is enough information to size it; do not estimate it
  yourself), small and testable. Do not assign points or time.

## Document template

In a story that needs refinement, mark unknown data as pending. In a ready story,
leave no unresolved markers. Include dependencies only when they apply.

```markdown
# <Title>

**Status:** Needs refinement / Ready for technical planning

## User story

As a <role>, I want <capability>, so that <benefit>.

## Context and problem

<Current situation and expected result, as provided by the user.>

## Business rules

<Confirmed rules only. Unconfirmed proposals are not requirements.>

## Acceptance criteria

<Omit the groups that do not apply.>

### Happy path

- Given <initial situation>, when <action>, then <observable result>.

### Errors

- <What happens on a failure that affects the business.>

### Edge cases

- <Extreme situation and expected result.>

## Out of scope

<Confirmed exclusions. New ones are recorded as proposals.>

## Confirmed decisions

- <Decision and reason when known.>

## Pending proposals

<Numbered proposals, marking those of the current round, or "None".>

## Open questions

<Unresolved questions, saying whether they block closing and why, or "None".>

## Dependencies

<Only when they apply: the dependency and its effect on the story.>
```

## Phase 2: Deliver

- **Ready story.** Update the content and set the status to "Ready for technical
  planning".
- **The user stops with blockers.** Leave the status as "Needs refinement" and
  highlight the decisions that prevent closing. If the user asks to finish anyway,
  do not mark the story as ready.
- **A ready story is reopened.** If blockers appear, set it back to "Needs
  refinement". If not, update the same file.
- **What to show.** During the rounds, the summary, the questions and the document
  location are enough. In the final delivery or when pausing, give the path and
  status and show the full document in a single `markdown` code block, ready to copy.
