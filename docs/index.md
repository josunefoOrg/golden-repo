---
title: golden-repo
---

# golden-repo

golden-repo is a GitHub template repository for creating secure agent and
security-tooling repositories. It provides a reusable baseline with standard
directories for `infra/`, `src/`, `docs/`, and `tools/`, plus security and
supply-chain workflows.

This page is published with GitHub Pages from the `main` branch `/docs` folder.

## Documentation

- [Architecture](architecture.md) - template architecture, layout, provisioning
  flow, and security baseline.
- [Setup](SETUP.md) - one-time GitHub App registration and installation steps.
- [Branch protection](branch-protection.md) - the `main` branch protection baseline.

## Provisioning

New repositories are provisioned with `tools/provision_repo.py` or the
self-service `Provision New Repository` workflow. Provisioned public and internal
repositories automatically get GitHub Pages enabled with a placeholder landing
page; private repositories are skipped.
