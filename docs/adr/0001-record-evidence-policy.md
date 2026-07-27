---
title: ADR-0001 Adopt the evidence policy
layout: default
parent: Decision records (ADRs)
nav_order: 2
---

# ADR-0001: Adopt an evidence policy for captured information

- **Status:** Accepted
- **Date:** 2026-07-27
- **Deciders:** golden-repo maintainers
- **Supersedes:** none
- **Superseded by:** none

## Context

The AI Agent Risk Management framework embedded in this template isolates and
protects *approved* grounding sources, but it treats grounding as an
authoritative layer and non-approved sources as risk to be excluded. It does not
address two realities:

- Captured information is not automatically trustworthy just because it was
  captured (see the "capture is not grounding" argument).
- Approved decisions can go stale quickly on fast-moving platforms, where an API
  that does not exist today may exist tomorrow.

A one-way membrane that only promotes vetted content into an authoritative layer
helps but is insufficient: it has no path for fresh, lower-trust evidence to
challenge stale approved guidance, and no requirement to record how such
conflicts are resolved.

## Evidence

| Claim | Source | Version | Observed | Trust tier |
| ----- | ------ | ------- | -------- | ---------- |
| Framework isolates approved grounding but excludes non-approved sources | `.github/agents/framework-compliance-reviewer.md` | repo `main` | 2026-07-27 | Approved |
| No ADR mechanism or freshness/provenance requirement existed before this change | golden-repo repository review | repo `main` | 2026-07-27 | Approved |

## Decision

Adopt the [Evidence policy](../evidence-policy.md) with controlled visibility
across all sources: approved guidance is the default but not the only visible
evidence, volatile technical claims are re-checked against current official
sources, every material claim carries source/version/observation date, fresh
lower-trust evidence may challenge but not silently override approved guidance,
material conflicts stop autonomous action and require human adjudication, and
each adjudication produces or updates an ADR.

## Consequences

- The Framework Compliance Reviewer and AI Risk & Security Advisor agents are
  extended to check and coach on evidence provenance, freshness, and the
  conflict-to-adjudication flow.
- Contributors must open an ADR when a material conflict is adjudicated or when
  approved technical guidance is reversed; the existing branch-protection and
  Code Owner review gate is where that decision is approved.
- Stale decisions are retired by supersession, not silent edits, preserving an
  auditable history.
