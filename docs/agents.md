---
title: Copilot agents
layout: default
nav_order: 10
---

# Copilot agents

This template can ship reusable Copilot custom agents under `.github/agents/` so
every repository generated from it starts with domain expertise built in. Agents
are Markdown files with a YAML front matter header (`name`, `description`,
`tools`, `model`) followed by the agent instructions. Agents are inert until
invoked, so they add no runtime cost to a generated repository.

## Included agents

- AI Risk and Security Advisor (`.github/agents/risk-security-advisor.md`).
  Advises on risk tier classification, Zero Trust architecture, threat detection,
  incident response, and compliance for enterprise AI agents on Microsoft Foundry.
- Framework Compliance Reviewer
  (`.github/agents/framework-compliance-reviewer.md`). Reviews repository content
  and configuration against the AI Agent Risk Management framework, covering Zero
  Trust, RBAC, guardrails, data protection, supply chain security, risk tiering,
  and mandatory controls, and reports compliance gaps with evidence-based
  remediation. The review rubric is embedded in the agent, so it works standalone
  in any generated repository. The framework compliance review workflow runs this
  agent on each pull request. See [Workflows](workflows.md).

## Recommended additional agents

- IaC agent. Reviews and authors infrastructure-as-code in `infra/` (Bicep or
  Terraform) and enforces tagging, network, and least-privilege conventions.
- Security agent. Reviews changes for security issues, validates the security
  baseline, and flags risky patterns.

## Adding or removing agents

- To add an agent, drop a new `.github/agents/<name>.md` file following the same
  front matter format.
- To remove an agent, delete its file.
