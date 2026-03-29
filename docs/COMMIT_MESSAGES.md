# Commit Messages

Use conventional commits with a scope that matches the workstream you touched. Keep each commit focused on one logical change, and prefer referencing the active task ID from [TASKS.md](/Users/monterey/Workspace/Projs/Tasmem/public-ads-scraping/TASKS.md) in the body when you are working against the execution plan.

## Format

```text
type(scope): short summary

Optional detail:
- what changed
- why it changed
- task or follow-up references
```

## Recommended Types

- `feat`: new platform capability or user-visible behavior
- `fix`: bug fix or regression repair
- `docs`: spec, onboarding, workflow, or architecture docs
- `test`: automated or manual validation changes
- `ci`: GitHub Actions, hooks, or pipeline automation
- `chore`: setup, dependency, or non-behavioral maintenance
- `refactor`: structural change without behavior change

## Scope Suggestions

- `workflow`
- `agent`
- `scrapers`
- `dashboard`
- `feature-extraction`
- `reverse-prompt`
- `infra`
- `orchestrator`

## Examples

```text
chore(workflow): add repo-level lint typecheck and verify entrypoints
```

```text
docs(bootstrap): rewrite local setup around shared python and npm commands

- standardize on npm run bootstrap
- document the 8081 agent API port
- reference optional E2E flow explicitly
```

```text
ci(workflow): replace narrow python smoke test with unified quality gates

- run lint, typecheck, test, security, and build in GitHub Actions
- keep branch coverage aligned with develop, staging, and main
```

```text
feat(orchestrator): add lightweight spec coverage and task sync tooling

- read SPEC.md, STATE.json, and ORCHESTRATOR_STATE.json
- report coverage and task status without adding a heavy runtime
```
