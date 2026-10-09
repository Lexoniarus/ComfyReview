# Entwicklungsroadmap: ComfyReview → Character Chronicles

**Dokumentrolle:** übergeordneter Produktphasenplan · **Status:** APPROVED_TARGET (ungefähre Entwicklungsrichtung; Phasengrenzen und Reihenfolge bleiben bei neuen Erkenntnissen überprüfbar)
**Geltungsbereich:** langfristige Evolution derselben ComfyReview-Codebasis · **Stand:** 2026-10-09
**Entscheidungsgrundlage:** [CRCC-001 bis CRCC-005](DECISIONS.md). Technischer IST-Zustand: [Projektstatus](project_status.md).

## Leitlinie

**ComfyReview ist die reale Ausgangsbasis. Character Chronicles ist das langfristige Ziel.** Der frühere Character-Chronicles-Versuch wurde verworfen, nicht „pausiert“. Seine Dokumente sind historische Referenzen, keine bindenden Anforderungen. Diese Roadmap ist bewusst **keine Kopie** des früheren Gesamt-MVPs. Namen, Schema-Versionen, Terminketten, Storyregeln und Spielmechaniken aus dem Archiv werden nur nach neuer Entscheidung übernommen.

## Reihenfolge

| Schritt | Phase | Ziel der Phase | Stand/Grenze |
| --- | --- | --- | --- |
| 0 | **ComfyReview-Basis** | laufende Review-, Generation-, Catalog- und Refactor-Grundlage ordnen und abnehmen | Bestehender Code; offene Akzeptanz-/Integrationsschritte im [Projektstatus](project_status.md) |
| 1 | **Card Battler** | funktionierenden, nachvollziehbaren Spielkern auf der vorhandenen Basis entwickeln | [Begrenzter Zielvertrag](CARD_BATTLER_TARGET.md), Detailkalibrierung und POCs offen; vorhandene Modell-/Entwicklungsbausteine sind noch kein spielbares Gesamtfeature |
| 2 | **Timeline** | zeitliche Interaktion und ihren Nutzen für die spätere Produktentwicklung klären und umsetzen | Umfang und UX zunächst **PROPOSED/POC**, keine übernommenen Academy-Zeitregeln |
| 3 | **Social Network mit Chat-Interaktion** | soziale Oberfläche, Interaktionsabläufe und zugehörige Zustandsgrenzen gestalten | erst durch neu entschiedene Verträge; historische Network-/Chat-Screens sind nicht bindend |
| 4 | **Storyline** | erzählerische Ereignisse, Fortschritts- und Verknüpfungslogik entwickeln | kein automatisches Zweijahres-/Cast-/Quest-Modell aus dem Archiv |
| 5 | **Visual-Novel-Content** | eigentliche VN-Inhalte, Szenen und ihre Ausspielung als letzte Produktstufe entwickeln | **zum Schluss**; erforderliche technische Vorarbeiten können in früheren Phasen ausdrücklich begründet werden, ohne VN-Content vorwegzunehmen |

Die Reihenfolge ist eine **grobe aktuelle Planungsannahme**, keine starre Phasen- oder Release-Sperre. POCs zu späteren Schnittstellen können begründet parallel stattfinden; ihre Ergebnisse sind keine vorgezogene Produktimplementierung. **Keine Termine oder Meilensteinnummerierung** werden aus dem früheren Chronicle-Versuch übernommen.

## Umsetzung pro Phase

1. **Scope festlegen:** definieren, was dieser Abschnitt und ausdrücklich **nicht** der nächste umfasst.
2. **Offene Entscheidungen/POCs erfassen:** Hypothese, Mess-/Akzeptanzkriterium, Risiken, Ergebnis und bewusst offene Alternativen im [POC-Register](POC_REGISTER.md) festhalten.
3. **Entscheidung dokumentieren:** erst eine aktive Entscheidung im [Register](DECISIONS.md) darf ein späteres Konzept als bindenden Teilvertrag übernehmen. Alte Dokumente bleiben trotzdem historisch.
4. **Vertikaler Slice:** geeignete Architektur, Persistenz, Tests und bedienbare Oberfläche gemeinsam entwickeln; keine ungeprüfte Komplettarchitektur vorab als umgesetzt beschreiben.
5. **Abnahme vor größerem Folgeausbau:** Produktive Slices nachweisen und Restumfang offenhalten; die nächste Stufe danach konkretisieren. Explorative POCs anderer Phasen dürfen ausdrücklich vorgezogen werden, ohne den Phasenplan als umgesetzt zu markieren.

**Kein Big-Bang-Umbau:** Die Einführung neuer Produktflächen darf aktuelle Review-/Generation-/Datenverträge nicht stillschweigend ersetzen. Erforderliche Migrations- und Produktentscheidungen werden einzeln versioniert.

## Technische Vorarbeit vs. eigentliche Content-Entwicklung

Bereits vor Phase 5 darf eine **explizit beschlossene** generische Schnittstelle nötig sein, etwa um spätere Story-/VN-Integration nicht zu blockieren. Das ist **keine Freigabe**, schon VN-Szenen, Cast-Listen, Dialogkampagnen, Assets oder den vollständigen alten Academy-Run zu implementieren.

**Offen:** konkrete Timeline-Semantik; Social-/Chat-Grenzen; Story-Modell; VN-Produktionspipeline; Zeitpunkt/Form der Umbenennung bzw. Vermarktung unter Character Chronicles, Packaging und eine eventuelle spätere Repo-/Modulaufteilung. Diese Entscheidungen werden nicht aus dem Archiv erraten.

Siehe [Dokumentationsindex](README.md), [offene POCs](POC_REGISTER.md), [spätere Bereiche](future/README.md).
