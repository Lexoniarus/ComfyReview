# Aktueller Entwicklungsstand — ComfyReview

**Dokumentklasse:** `IN_PROGRESS` – Code-/Arbeitsstand mit offenen Integrations- und Abnahmegrenzen.

**Referenz:** ComfyReview-Code [`a5f4131`](https://github.com/Lexoniarus/ComfyReview/commit/a5f4131bb76c1ff655892d287d19fcd401917d32) (2026-10-08, **vor** Dokumentenimport), Nutzer-Einordnung vom 2026-10-09. **Kein Releasebericht.**

## Statusvokabular

- **Im Code vorhanden:** Funktionalität/Adapter ist nachweisbar.
- **In Runtime verdrahtet:** Vom aktiven App-Bootstrap, einer API oder UI verwendet.
- **Aktiv in Arbeit/POC:** Weiterentwicklung läuft, Integrations-/Produktabnahme **offen**; vorhandene Tests decken nur ihren jeweiligen Scope ab.
- **Abnahme offen:** Implementierung und operative Freigabe sind zwei getrennte Dinge.
- **Zukunft/Option:** Hypothese oder fachliches Ziel, kein genehmigter Implementierungsauftrag.

## Bestandsaufnahme

| Bereich | Codebasis / belegbarer Stand | Arbeit / noch nicht nachgewiesen |
| --- | --- | --- |
| Review / Ranking / Arena / Curation | Runtime/API/Repositories und Tests vorhanden; [Audit](IMPLEMENTATION_AUDIT.md) | Produktentwicklung insgesamt geht weiter; keine pauschale „fertig“-Aussage |
| Generator / ComfyUI | Jüngste Überarbeitung: Compiler, Blueprint v4, GenerationService, Lifecycle und Reconcile sind verdrahtet. [Code](../comfyreview/application/generation.py) | Reale Geräte-/Providerzustände, Nutzungsakzeptanz und weitere Verbesserungen bleiben separat |
| Prompt-/LoRA-Katalog | Versionierte Revisionen, atomare Promptverarbeitung, Katalog und API vorhanden. [Catalog](../routers/api_v2/catalog.py) | Katalog-Normalisierung und Datenzuordnung gerade in Überarbeitung |
| Canonical SQLite | **Schema v18 im Code**, explizite Migrationen und Validierung. [Schema](../comfyreview/repositories/sqlite/canonical_schema.py) | **Private Runtime-DB muss nicht bereits v18 verwenden.** Editorial Mapping, Rehearsal, echter `--replace`-Cutover und Optimierungen sind nicht durch den Code-Commit als erledigt erwiesen |
| Card Battler | Aktive POC-Entwicklung: typisierte Modelle, Mapping, deterministische Mechaniken, Trait-Entwicklung und Visual-Prompt-Projektion mit Tests. [POC](pocs/card-battler.md) | Keine vollständig nutzbare Karten-Sammlung, Deckverwaltung, PvE-Matchengine oder Browseroberfläche im geprüften Branch |
| Character Chronicles | [Langfristige Vision](PROJECT_EVOLUTION.md) und importierte Texte vorhanden | Kein automatisch akzeptierter technischer Migrationspfad, MVP, Releaseplan oder Architektur-Commitment |

## Nächste fachliche Richtung (nicht gleichbedeutend mit Fertigstellung)

Der **Card Battler** ist der aktuelle konkrete POC-/Entwicklungsschwerpunkt.
Die derzeitige **ungefähre** Reihenfolge danach ist **Timeline → Social
Network mit Charakter-Chats → Storyline → Visual-Novel-Content zuletzt**.
Die Timeline kann ein eigenständig prüfbarer erster Social-Slice sein,
bevor die umfassendere Plattform/Chat-Interaktion entsteht; das ist
**kein bereits beschlossener eigener Release**. Die **zwei
Academy-Jahre in Kobe sind bestätigter Weltkern**, aber
keine zusätzlich verpflichtende Implementierungsphase.
[Weltvision](character-chronicles/vision/world.md).

Damit ist **kein** weiterer Code als bereits implementiert behauptet:
Timeline, Social-/Chat-Plattform, Storyline und VN-Content sind in der
geprüften ComfyReview-API **noch keine fertig integrierten Funktionen**.
Academy-/Schuljahressimulation ist ebenfalls **nicht implementiert**:
Das bestätigte Worldbuilding verpflichtet nicht zu den früheren
Kalender-, Guardian- oder Datenbankverträgen.
Freistellung/Matting und das konsistente Montieren von Szenenbildern
bleiben für den VN-Teil gesondert zu prüfende technische Risiken.

[Projektentwicklung und Begründung](PROJECT_EVOLUTION.md#gewonnene-reihenfolge-aus-den-bisherigen-versuchen)
· [Card-Battler-POC](pocs/card-battler.md).

## Vorsicht bei historischen Statusmeldungen

Einige ältere Dokumente berichten über erfolgreiche persönliche Datenbank-Upgrades, Live-Smokes und konkrete Zahlen. Das sind **historische Operator-Berichte**. Die zugehörigen lokalen Datenbanken, Reports, Mapping-Dateien und deren aktueller Zustand sind nicht versioniert. **Bitte nicht mit dem heutigen tatsächlichen Cutover verwechseln.**

Die [GitHub-CI für `a5f4131`](https://github.com/Lexoniarus/ComfyReview/actions/runs/37769483557) war erfolgreich. Ein zusätzliches [Quality-Run auf dem codegleichen Dokumenten-Commit](https://github.com/Lexoniarus/ComfyReview/actions/runs/37901248379) war ebenfalls erfolgreich. CI belegt automatisierte Tests für genau diesen Code, nicht das Ende der Entwicklung.

## Pflege

Ändert sich die Implementierung, diese Übersicht und [Code-Audit](IMPLEMENTATION_AUDIT.md) anhand eines **neuen konkreten Commits** nachziehen. POC-Ergebnisse gehören in [POCs](pocs/README.md); neue Produktentscheidungen in [Decision Policy](DECISION_POLICY.md). Keine fertigen Meilensteine aus dem bloßen Vorhandensein von Code oder alten Zielverträgen ableiten.
