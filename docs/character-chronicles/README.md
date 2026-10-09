# Character Chronicles – Übersicht

**Dokumentklasse:** `WORKING_VISION` · **Rolle:** Zielbild-Index · **Stand:** 2026-10-09  
**Verhältnis:** ComfyReview ist die **laufende technische Basis**; Character Chronicles ist die **langfristige Produktrichtung**. Das ist kein zweites heute fertig implementiertes Produkt und keine automatische Wiederaufnahme der verworfenen Chronicle-Codearchitektur.

## 1. Aktuelles fachliches Zielbild

Die **[bereinigte Vision](vision/README.md)** ist der richtige Einstieg. Sie erklärt die derzeitige Arbeitsorientierung ohne versteckte Altverträge:

1. [Card Battler](vision/card-battler.md) – aktueller Schwerpunkt: POC zunächst spielerseitig erprobbar machen.
2. [Timeline](vision/timeline.md) – nächster begrenzter sozialer/zeitlicher Interaktionsslice.
3. [Social Network mit Charakter-Chats](vision/social-network.md) – breitere Plattform aufbauend auf der Timeline.
4. [Storyline](vision/storyline.md) – Ereignisse, Figurenentwicklung und Fortschritt; [Academy/Schuljahr](vision/academy-and-world.md) bleibt ein möglicher Weltkontext, **keine zusätzliche Pflichtphase**.
5. [Visual-Novel-Content](vision/visual-novel.md) – **zuletzt**, mit möglichen früheren kleinen Technik-POCs für Matting und Szenenkomposition.

**Keine** dieser Seiten setzt bereits einen genauen MVP, Release-Termin, verbindliche Datenbankschemas oder zwingende technische Etappen fest.

## 2. Ausführliche Ideen und Originaldokumente

[24 importierte Quelltexte](sources/README.md) sind in `sources/` zugänglich. Einige Texte enthalten **später ergänzte inhaltliche Zielideen**, andere **frühere Card-Battler-/M6-/UI-/Schema-Verträge**. Ihre früheren Aussagen über „verbindlich“, „DECIDED“, „abgeschlossen“ und „implementiert“ gelten **nur innerhalb der überlieferten Quelle**.

Die [Herkunfts- und Themenmatrix](sources/SOURCE_RELATIONSHIP.md) hilft, die 24 Texte zur Gegenwart und zum früheren Code einzuordnen. Wenn etwas davon künftig bestätigt wird, muss das **ausdrücklich** in einem aktiven Vision-/POC-/Entscheidungsdokument erfolgen.

## 3. Wirklich früher implementierter, dann verworfener Ansatz

[Historischer ZIP-Code-Audit](HISTORICAL_CODE_AUDIT.md) beschreibt die im bereitgestellten `CharacterChronicle.zip` vorhandene ältere Codebasis (Vite/TypeScript, Trial-/M6-Services, Schema v58), **nicht** ComfyReviews aktuellen FastAPI-/Jinja-/SQLite-v18-Stand.

Der [ältere umfangreiche Gesamtentwurf](history/full-mvp-draft-2026-08.md) bleibt separat unter `history/`. **Alte technische Lösungen können Erkenntnisse liefern, aber sie bestimmen nicht den zukünftigen Aufbau.**

## 4. Technische Gegenwart und noch offene Punkte

Für das echte Code-Inventar: [ComfyReview Implementation Audit](../IMPLEMENTATION_AUDIT.md); für gerade laufende Arbeit: [Active Work](../ACTIVE_WORK.md) und [Card-Battler-POC](../pocs/card-battler.md). [Offene Entscheidungen](../OPEN_DECISIONS.md) betreffen unter anderem die nächste Integration, Detailmechaniken und spätere Architektur.

## Fehlende Vorgängerquellen

**Nicht mehr als Quellen unbekannt:** Einige in alten Texten referenzierte Dokumente sind **nicht im ComfyReview-Git-Tree**, aber im bereitgestellten historischen `CharacterChronicle.zip` auffindbar. Das betrifft u. a. `docs/mvp/foundation/`, `docs/mvp/acceptance/m4/`, `docs/mvp/acceptance/m6.7/02-rolling-loop.md` und `docs/mvp/product/historical-reference-bootstrap-and-evaluation.md`. Sie sind historische Evidenz, **keine** aktuelle Produktfreigabe. [Exaktes Inventar](HISTORICAL_CODE_AUDIT.md).
