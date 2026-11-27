# Roles

Each role has things the implementer must respect and things the reviewer must check.
These lists are a floor. The repository's own `CLAUDE.md`, `AGENTS.md` and relevant
skills add more. Read them first. Do not apply conventions from another repository.

For all roles:

- Use only the plan, the story, the contract and the repository. Do not invent
  requirements.
- Prefer the repository's existing patterns. Cite the file you followed.
- Do not add dependencies. If one is needed, return `needs_decision`.
- Do not generate tests unless the substep asks for them or the repository convention
  requires them with new behavior. The plan decides.

## backend

Implementer:

- Follow the repository layering and naming.
- Define interfaces and DTOs before logic when the substep introduces a contract.
- Follow the contract exactly: routes, payloads, status codes, error codes.
- One migration per substep that changes the model. Do not edit old migrations. The
  final migration set is a decision for the user if the feature is unreleased.

Reviewer checks:

- Acceptance criteria of the plan steps are met by the code.
- The implementation matches the contract. List any difference.
- Validation, limits, error codes and edge cases from the story are covered.
- Layer boundaries respected. No domain types leaking where the repository forbids it.
- Migration matches the model. Snapshot is consistent.
- Behavior with concurrency, nulls and duplicates when the story involves them.

## frontend

Implementer:

- Build against the contract. Use mocks until the real backend is available, using
  the mocking approach the repository already has.
- Follow the repository's component, state and styling patterns.
- Texts go through the localization mechanism when the story requires it. Do not
  translate content written by the user.
- Handle loading, empty, error and slow-response states.

Reviewer checks:

- Acceptance criteria of the plan steps are met by the UI behavior.
- Behavior matches the contract, including error codes and parameters.
- Async risks: stale responses overwriting newer state, lost user input, double
  submits, unhandled failures.
- Accessibility: labels, error association, keyboard use, focus.
- Localization keys exist for every supported language when the story requires it.

## iac

Implementer:

- Follow the repository's infrastructure conventions and existing modules.
- Change only the paths in `scope`.
- Never put secret values in files. Name the secret and its purpose only.

Reviewer checks:

- Resources match the plan and nothing extra is created.
- Naming, tags, access and networking follow the existing modules.
- No secret values. Least privilege for identities and roles.
- The change is safe to deploy: no destructive replacement of existing resources
  without the plan saying so.
- Any deployment-impacting choice is marked as a decision for the user.
