---
title: Decision records (ADRs)
layout: default
nav_order: 12
has_children: true
---

# Architecture Decision Records (ADRs)

Architecture Decision Records capture significant, durable decisions and the
evidence behind them. They are the required output of the adjudication step in
the [Evidence policy](../evidence-policy.md): when fresh evidence conflicts with
approved guidance, a human decides and the decision is recorded here.

## When to write an ADR

Write a new ADR, or update/supersede an existing one, when any of these happen:

- A material conflict between sources is adjudicated by a human.
- Approved technical guidance is reversed or changed because a capability, API,
  limit, or version changed (for example, an endpoint that did not exist before
  now exists).
- A decision is made that future contributors or agents will need to understand
  and that should not be re-litigated silently.

## How ADRs handle staleness

ADRs are never edited to quietly change meaning. When a decision becomes stale,
create a new ADR that **supersedes** the old one and set the old ADR's status to
`Superseded by ADR-NNNN`. The supersession chain preserves history while making
the current decision unambiguous. This is how a good-but-now-stale decision is
retired instead of silently misleading later work.

## Numbering and status

- Files are named `NNNN-short-slug.md`, zero-padded, starting at `0001`.
- Status is one of `Proposed`, `Accepted`, `Superseded by ADR-NNNN`, or
  `Deprecated`.
- Copy [`0000-adr-template.md`](0000-adr-template.md) to start a new record.

## Records

Individual records appear as child pages in the navigation. The template
(`0000`) is not a real decision; it is the starting point for new ADRs.
