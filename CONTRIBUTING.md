# Contributing

Thanks for helping improve Public Ads Platform.

## Before You Start

- Read [`LOCAL_BOOTSTRAP.md`](./LOCAL_BOOTSTRAP.md) for the repo-level setup flow and [`platform/README.md`](./platform/README.md) for component-level architecture context.
- Review [`SPEC.md`](./SPEC.md), [`AGENTS.md`](./AGENTS.md), and [`TASKS.md`](./TASKS.md) before starting larger changes so your work aligns with the current execution plan.
- Use local or placeholder credentials only. Never commit `.env` files, service-account keys, or private datasets.
- Prefer small, reviewable pull requests over large mixed changes.

## Local Development

```bash
npm run bootstrap
cp .env.example platform/.env  # if bootstrap did not create it yet
```

Run the fast deterministic test suite before opening a pull request:

```bash
npm run verify
```

## Project Expectations

- Keep the local-first development story working without mandatory cloud dependencies.
- Do not introduce committed secrets, service-account material, or non-public sample data.
- Update documentation when setup steps, interfaces, or workflows change.
- Call out scraping, policy, or legal considerations when a change affects how data is collected.
- Keep branch targets aligned with the documented `develop -> staging -> main` promotion flow unless the team explicitly decides otherwise.

## Pull Request Checklist

- Explain the user-facing or developer-facing impact.
- Include verification steps or test output.
- Mention any follow-up work that should happen after merge.
