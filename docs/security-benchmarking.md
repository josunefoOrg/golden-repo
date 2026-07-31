---
title: Security benchmarking
layout: default
nav_order: 14
---

# Security benchmarking (optional)

Repositories created from this template host security AI agents (SOCBot- and
PostureIQ-style projects). Beyond the [framework compliance review](workflows.md#framework-compliance-review),
which checks that *changes* follow the AI Agent Risk Management framework, you
can optionally benchmark the *capability* of the agent itself against
realistic security tasks using [ACES](https://github.com/microsoft/ACESEvals)
(Agent Capability Evaluation Suite; internal Microsoft codename **SABER**).

ACES is not part of required CI and is not enabled by default. It is a scaffold
you opt into once your agent exists and you have authored eval task configs for
it.

## What ACES does

ACES loads YAML task definitions, renders prompts, and produces native
[`inspect_ai`](https://inspect.ai-safety-institute.org.uk/) `Task` objects.
Docker sandboxes, tool execution, scoring, and the agent loop are handled by
`inspect_ai`'s built-in primitives — ACES itself is a thin library, not a
server. Tasks range from CTF-style exploitation to log-investigation scenarios
(for example the ExCyTIn domain shipped with ACES).

## What this template provides

`.github/workflows/agent-security-benchmark.yml` is a manual-dispatch workflow
that wraps `inspect eval <task-path> --model <model> -T agent=<agent>`. It:

- Runs only on `workflow_dispatch` — it never gates pull requests or merges.
- Fails fast with a clear message if the eval task path is missing or if model
  credentials are not configured, rather than silently skipping.
- Installs `uv`, ACES (`saber`), and `inspect-ai`, then runs the eval and
  uploads the resulting logs as a workflow artifact.

The workflow is a scaffold: it does not ship with eval task configs, because
those are specific to the agent implemented in a given provisioned repository.

## One-time setup (per provisioned repository)

1. **Author eval task configs.** Add YAML task definitions describing the
   security scenarios to benchmark your agent against, under `evals/` (the
   workflow's default `eval_path`). See the
   [ACES quickstart](https://github.com/microsoft/ACESEvals#run-your-first-evaluation)
   and its `domains/` examples for the task config format.
2. **Configure model credentials as secrets:**
   - `AZUREAI_OPENAI_API_KEY`
   - `AZUREAI_OPENAI_BASE_URL`
   - `AZUREAI_OPENAI_API_VERSION`

   ```bash
   gh secret set AZUREAI_OPENAI_API_KEY --repo <org>/<repo> --body "<key>"
   gh secret set AZUREAI_OPENAI_BASE_URL --repo <org>/<repo> --body "<url>"
   gh secret set AZUREAI_OPENAI_API_VERSION --repo <org>/<repo> --body "<version>"
   ```
3. **Run it:** dispatch the workflow (`gh workflow run agent-security-benchmark.yml`)
   with `eval_path`, `model`, and `agent` inputs, or accept the defaults
   (`evals/`, `azure/gpt-4.1`, `react`).

## Azure DevOps internal users

If your organization consumes ACES from Azure DevOps (`oss_saber`) instead of
GitHub, adapt the "Install ACES" step to install from the ADO git URL instead
of `https://github.com/microsoft/ACES.git`, per the
[ACES README](https://github.com/microsoft/ACESEvals#readme).

## Why this is optional, not required

Running ACES consumes model-provider quota/cost per invocation and requires
Docker sandboxes, so it is not suited to running on every pull request by
default. Treat it as a benchmarking tool to run periodically or before a
release, not a required status check.
