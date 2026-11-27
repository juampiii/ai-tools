# Escalation policy

Use this when a decision appears during intake or execution. First try to decide.
Ask the user only when the rules below say so.

## Decide alone and log it

Decide when all of these are true:

- The decision is easy to undo.
- The plan, the story, the repository conventions or the user's global rules already
  point to an answer, or one option is clearly the simplest.
- It does not touch an item in the list below.

Write the decision in `decisions.md` before you act: what, why, the alternative
discarded, and how to undo it. The summary goes into the pull request description.

Style and convention questions are never questions for the user. Follow the repository
conventions and the user's rules. If the rule is missing, choose the repository's
existing pattern and log it.

## Ask the user

Ask when any of these is true:

- **Data model or migration.** New entities, changed columns, changed relationships,
  or anything that needs a migration.
- **Public contract.** Endpoints, payloads, error codes, event shapes.
- **Business rule missing from the story.** Behavior the user has not defined.
- **New library or package.** A new production dependency is always a question. A new
  development or test dependency is a question unless the repository already uses a
  library for that purpose.
- **Deployment or infrastructure.** How the application is built, packaged, hosted or
  configured in an environment, including IaC resources.
- **Conflict.** The story, the plan and the code disagree.
- **Low confidence.** You cannot recommend an option and say why.

## How to ask

- Queue the question in `state.json` with a recommendation, the options, the impact
  of each one, and the substeps it blocks.
- Keep working on anything that does not depend on it.
- Ask all queued questions together with `AskUserQuestion`: when nothing else can
  move, at the end of execution, or earlier if the answer would change a lot of work.
- Put your recommended option first.
- Write the answer in `decisions.md` as a user decision.

## Safety rules that never change

- Do not merge pull requests.
- Do not publish, push or open pull requests unless the user allowed it at intake.
- Do not run destructive commands on data, branches or containers you did not create.
