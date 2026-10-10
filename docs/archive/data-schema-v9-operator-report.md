# Frühere Schema-v9-Liveprüfung – historischer Operatorbericht

**Dokumentklasse:** `HISTORICAL_LOG` · **Rolle:** früherer Operatorbericht, **keine aktuelle Datenbankinventur.**

Die folgende Passage stammt aus einer älteren Fassung der ComfyReview-Datenarchitektur. Sie berichtet über Datensätze und Backups zu früheren Schema-v4-bis-v9-Migrationen und lokale Rehearsals. **Die aktuell im Code unterstützte Version v18** und der gegenwärtige private Cutover müssen gesondert überprüft werden. Die historischen Datenbanken und Backup-Dateien sind nicht Teil des Repositories.

[Aktuelle Datenarchitektur](../DATA_ARCHITECTURE.md) · [Implementierungsstatus](../project_status.md) · [Betriebs-/Migrationsanleitung](../OPERATIONS.md).

---

## 10. Historical operator record: earlier schema-v9 verification

> **Not today's live database snapshot.** The following numbers and migration
> steps were recorded during the earlier schema-v9 operation. The current
> application code declares **schema v18**, and the real runtime database
> is not present in the repository. This section is retained as historical
> provenance, not a current row count or newly validated cutover.
> [Current implementation audit](../IMPLEMENTATION_AUDIT.md).

The previously reported schema-v9 database contained 379 generations, 379 images, 379
sampler stages, 729 prompt components, 729 immutable first revisions, 275
recovered compositions and 1,280 ordered composition memberships. All 379
images have output role, output index and a verified content hash. The existing
5,534 review events, 1,257 Arena matches and three Curation assignments remain
canonical facts.

The explicit v6-to-v7 migration was rehearsed on a byte-identical copy, then
run against the stopped live application. Both upgrades created their own
SQLite backup. The live migration preserved every component, revision,
composition, generation and rendered prompt snapshot while creating 4,061
ordered revision atom usages. The later explicit v7-to-v8 upgrade was
rehearsed on a database copy, backed up and applied with the application
stopped. It added workspace preferences, generation profiles and normalized
profile/generation LoRA relations without changing stable image, generation,
component, revision or composition IDs. The explicit v8-to-v9 upgrade was
rehearsed on a read-safe SQLite copy, backed up and applied with ComfyReview
stopped on 2026-10-03. It preserved all 379 generation/image identities and
added content/canvas settings. That verified live database's `user_version` is 9,
`integrity_check = ok`, and `foreign_key_check` returns no rows. The verified
pre-v7 backup remains schema v6 with all 729 revisions.

The application requires schema v18. No older database is silently changed at
startup. `canonical-db upgrade` first migrates and validates a new database
file and preserves the source; installation of the validated output is a
separate controlled step.
The v10-to-v11 migration creates no image classifications by itself; the
operator runs `canonical-db rebuild-image-geometry` explicitly after upgrade.

Historical completion was rehearsed from a verified v4 backup through the full
v4-to-v6 upgrade and all four fresh audit/import stages. The same ordered
sequence then ran against the already-upgraded live v6 database. Each live
import created its
own validated backup before writing. Final `integrity_check`, foreign-key,
schema, identity, protected-field, provenance, read-only-reader and
canonical-only startup checks passed. Repeated rehearsal imports created no
additional facts.

Normal startup never performs this sequence and never opens a legacy database.
The ignored detailed reports and backups remain the operational evidence; this
document records only non-sensitive aggregate results.

The design must not duplicate prompt atoms per review or materialize the full
Cartesian product of possible prompt combinations. Persist combinations when
they are explicitly authored, generated, curated or uniquely reconstructed. An
unused authored template or revision remains canonical catalog data.

In that historical validation, Frontend V2 used the recorded data. Exact memberships were authoritative for
the 363 linked generations. Any scope fallback for the sixteen unresolved
generations must be the smallest read-only policy justified by their explicit
diagnostics; it must not read legacy databases, paths, directory names or
sidecars as runtime truth.

Before migrating a derived projection, prefer a direct canonical query, then a
SQL view. Only measured needs justify a materialized projection and worker.

