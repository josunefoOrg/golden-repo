---
title: ADR-0000 Template
layout: default
parent: Decision records (ADRs)
nav_order: 1
---

# ADR-NNNN: Short decision title

- **Status:** Proposed | Accepted | Superseded by ADR-NNNN | Deprecated
- **Date:** YYYY-MM-DD
- **Deciders:** names or roles of the humans who adjudicated
- **Supersedes:** ADR-NNNN (or "none")
- **Superseded by:** ADR-NNNN (or "none")

## Context

What situation forced a decision? If this decision resolves a conflict under the
[Evidence policy](../evidence-policy.md), state the approved guidance and the
fresh evidence that challenged it.

## Evidence

List each material claim the decision depends on, with full provenance. Do not
record a claim without its source, version, and observation date.

| Claim | Source | Version | Observed | Trust tier |
| ----- | ------ | ------- | -------- | ---------- |
| Example: endpoint `/v2/foo` exists | https://official.docs/foo | api 2026-07 | 2026-07-27 | Official (current) |

## Decision

The decision that was made, stated plainly.

## Consequences

What becomes easier or harder as a result. Note any follow-up actions, and any
conditions under which this decision should be revisited (for example, a
capability that is expected to ship and would make this decision stale).
