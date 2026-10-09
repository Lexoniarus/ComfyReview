# Projection Audit

> **Historical record (classified 2026-10-09):** This captures an earlier implementation slice, not the current runtime contract. For current behaviour use [Project Status](../project_status.md), [Architecture](../ARCHITECTURE.md) and [Data Architecture](../DATA_ARCHITECTURE.md).

Status: completed on `refactor/review-boundary`, 2026-09-30.

This audit applies the required order to every remaining derived dataset:
direct canonical query first, canonical SQL view second, and materialization
only after a measured need. No current projection has evidence that justifies
a replacement background worker.

## Decisions

| Dataset | Current legacy mechanism | Canonical decision | Cutover consequence |
| --- | --- | --- | --- |
| Image ranking | `images.sqlite3` worker projection plus rating tables | Direct repository query over `images`, `review_events`, lifecycle and Curation facts | Existing `RankingService` already follows this decision; remove the legacy image projection consumers |
| Prompt performance | `prompt_tokens.sqlite3` plus `prompt_ratings.sqlite3` | Direct repository query over generation prompt snapshots and review events, with prompt atoms normalized at the repository boundary | Replace page/store reads; no prompt-rating materialization |
| Prompt-token statistics | Worker-maintained token rows and aggregate rows | Direct canonical query with deterministic atom parsing and request-time aggregation | Delete token/rating projection writes and cursor state after parity tests |
| Combo statistics | Eager `combo_prompts.sqlite3` rebuild | Query observed canonical generations/compositions only | Do not rebuild or copy the Cartesian catalog product |
| Recommendations | Legacy combo and parameter aggregate queries | Direct query over observed generation parameters, concrete prompt revisions and review events | Preserve filters and scoring behavior without a writable recommendation truth |
| Best-image lookup | `images.sqlite3` plus token-overlap store | Direct canonical image/review query against rendered prompt snapshots | Keep paths as result attributes, never lookup identity |
| Worker jobs and cursors | `mv_jobs.sqlite3` and `mv_state` | Delete after all listed readers use canonical repositories | Review mutations stop requesting catchup jobs; application lifespan stops owning the legacy worker |

## Why no new materialized worker

The current local dataset and request patterns do not demonstrate a measured
latency or throughput requirement that cannot be met by indexed canonical
queries plus bounded in-process aggregation. The existing worker exists to
synchronize several legacy databases, not because the derived results require
asynchronous materialization.

If later profiling shows a real need, each materialization must have its own
idempotent, rebuildable projection behind a small registry. A general-purpose
replacement for the legacy worker is explicitly not approved by this audit.

## Cutover invariants

- Every page reads canonical facts or a rebuildable read-only view.
- No route, service or provider writes a derived statistics database.
- Prompt atoms are deterministic derivatives of stored prompt snapshots and
  may be rebuilt without changing catalog revisions or review events.
- Only observed or explicitly authored compositions are queried. The full
  possible catalog product is never persisted.
- Removing jobs/cursors happens only after the last active runtime consumer is
  removed and route parity tests pass.
- Legacy projection databases remain read-only migration evidence until their
  consumers are gone; they are never dual-written with canonical state.
