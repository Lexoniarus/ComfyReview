# Projektentwicklung: Von ComfyReview zu Character Chronicles

**Dokumentklasse:** `WORKING_DIRECTION` – aus POCs abgeleitete Priorität, keine feste Roadmap oder Architektur.

**Stand: 2026-10-09.** Dieses Dokument beschreibt eine **Richtung**, keine freigegebene Gesamtarchitektur und keinen verbindlichen Implementierungsplan.

## Ein Produkt in Entwicklung, eine langfristige Vision

**ComfyReview ist der aktuelle, aktive Entwicklungsstand**: Eine lokale Anwendung zum Erzeugen, Prüfen, Vergleichen, Kuratieren und Auswerten von ComfyUI-Bildern. Das Projekt ist **nicht abgeschlossen**. Generator, Datenmodell und Nutzerabläufe werden weiter überarbeitet.

**Character Chronicles ist die langfristige Produktrichtung, in die sich ComfyReview entwickeln soll.** Das bedeutet **nicht**, dass alle heute aufgeschriebenen Mechaniken oder alle technischen Schritte später genau so umgesetzt werden. Die Entwicklung erfolgt iterativ mit Proofs of Concept (POCs), Tests, Experimenten und bewussten Architekturentscheidungen. Ein Teil des aktuellen Codes kann tragfähig bleiben; anderer Teil kann ersetzt werden.

```text
ComfyReview — realer, laufend veränderter Code
      │
      ├─ Generator-/Katalog-/Datenbank-Refactoring
      ├─ Card-Battler-POC und weitere fokussierte Experimente
      │
      └─ Erkenntnisse, Belege, verworfene Ideen
                      │
                      ▼
         Character Chronicles — langfristiges Zielbild
         (konkreter Weg, Umfang und Architektur offen)
```

Das ist eine **Arbeitslogik**, keine Roadmap mit Releasegates. Ein POC darf sich als Sackgasse erweisen und sein Modell darf bei der nächsten Iteration ersetzt werden.

**Anders als der technische Weg ist die Zielwelt nun bestätigt:**
Kobe/Japan ab 2032, bodenständige Near Future, zwei Academy-Jahre
für junge Erwachsene, eine global etablierte Social- und Battler-Kultur,
der neu ankommende Protagonist und eigenständige Figuren mit
Beziehungen und Biografien. Die **VN mit Dating-Sim-Elementen** ist
langfristig der erzählerische Mittelpunkt. [Bestätigte Welt](character-chronicles/vision/world.md).
Das Weltbild darf durch **ausdrückliche** Entscheidungen verfeinert
werden; neue POC-Ergebnisse bedeuten nicht automatisch, dass
Schauplatz, Academy oder kulturelle Grundsituation wieder offen sind.

## Gewonnene Reihenfolge aus den bisherigen Versuchen

**Stand 2026-10-09 – bewusst ungefähr, keine starre Roadmap:**
Die Ideen für Card Battler, Worldbuilding und Character Chronicles haben
erst im Laufe der Experimente zusammengefunden. Der frühere Chronicle-Ansatz
ging mit umfassender Architektur und VN-/Academy-Planung voraus, bevor die
heute wichtigeren spielerischen Grundlagen hinreichend geklärt waren.
Diese Erfahrung begründet **die Reihenfolge der nächsten Schwerpunkte**,
nicht die Wiederherstellung des früheren Projekts.

| Orientierung | Spielerisches Ziel | Was damit ausdrücklich **nicht** festgelegt ist |
| --- | --- | --- |
| **1. Card Battler – zuerst** | Den aktiven [Card-Battler-POC](pocs/card-battler.md) vom getesteten Bibliothekscode zu einem tatsächlich funktionierenden, spielerisch prüfbaren Kartenloop weiterentwickeln | Kein alter Sieben-Phasen-Plan, kein fertig spielbares PvE, keine unveränderliche 40-Karten-Regel |
| **2. Timeline – anschließend** | Eine verständliche zeitliche/soziale Oberfläche und Interaktionen zunächst als begrenzten Slice erproben; Grundlage für die spätere Plattform | Noch kein beschlossenes Datenmodell, keine vollständige Social-Network-Runtime und keine feste Academy-Kalendermechanik |
| **3. Social Network mit Chat-Interaktion** | Timeline/soziale Präsenz zu einer Plattform mit Charakter-Chats und weiteren Interaktionen ausbauen | Kein schon beschlossener LLM-, RAG-, Feed-, Relationship- oder Provider-Vertrag |
| **4. Storyline** | Figuren, Beziehungen und Ereignisse über die **zwei bestätigten Academy-Jahre in Kobe** erzählerisch entwickeln | Keine separate verpflichtende Academy-Technikphase; genaue Kalendertage, Story-Reducer und alte Datenverträge sind nicht gesetzt |
| **5. Visual-Novel-Content – zuletzt** | Die zuvor entwickelten Spiel-/Interaktions-/Storysysteme erst am Ende durch eigentliche szenische VN-Inhalte und konsistente visuelle Präsentation ergänzen | Keine vorgezogene große Sprite-/Szenenproduktionsphase. Kleine frühere Feasibility-POCs für Freistellung, Segmentierung/Matting und Szenenkomposition bleiben sinnvoll |

**Timeline und Social Network sind fachlich eng verwandt, werden aber für die
Entwicklungsorientierung als aufeinander aufbauende Schwerpunkte bezeichnet:**
erst den Timeline-Slice erproben, danach die breitere Plattform samt Chat.
Ebenso ist **Storyline** der spätere Entwicklungsbereich; die **zwei
Academy-Jahre sind bereits ein bestätigter Welt- und Zeitrahmen**, aber
kein zusätzlicher zwingender Implementierungsmeilenstein.
Die eigentliche **VN-Content-Entwicklung ist zuletzt**, ohne ihren
langfristigen erzählerischen Stellenwert zu schmälern.

Diese fünf Punkte sind eine **veränderbare Richtung**, kein festgelegter MVP,
kein formaler Release-Gate-Plan und keine Übernahme früherer M4-/M6-/Schema-
oder Frontend-Verträge. Kleinere übergreifende POCs können aus technischen
Gründen vorgezogen werden, ohne dass damit späterer Produktumfang als fertig
oder beschlossen gilt. [Einfaches Zielbild](character-chronicles/vision/README.md)
und [offene Entscheidungen](OPEN_DECISIONS.md).

Als **späterer fachlicher Meilenstein** ist außerdem die
Unterscheidung zwischen der in der Spielwelt gültigen
Figuren-/Ereigniswahrheit und der technischen Bildproduktion
bestätigt. Ein Qualitätsgewinn beim Rendering ist nicht
automatisch ein Ereignis oder eine Veränderung der Figur
innerhalb der Geschichte. Die genaue Realisierung wird später
geprüft; daraus entsteht **keine sechste verpflichtende
Entwicklungsphase und kein heutiges Release-Gate**.
[Bestätigter Scope](CONFIRMED_CONSTRAINTS.md#späterer-fachlicher-meilenstein-spielwelt-und-technische-bildproduktion).

## Was heute tatsächlich vorhanden ist

[ComfyReview-Ist-Analyse](IMPLEMENTATION_AUDIT.md) verwendet den Anwendungscode des Commits [`a5f4131`](https://github.com/Lexoniarus/ComfyReview/commit/a5f4131bb76c1ff655892d287d19fcd401917d32), also den Code **vor** dem reinen Dokumenten-Import [`76d71f9`](https://github.com/Lexoniarus/ComfyReview/commit/76d71f9c7723701664785aeaf07e0d7375a4f36a).

Daraus belegbar: FastAPI, Canonical SQLite v18 (als **im Code unterstütztes Schema**, nicht als Nachweis des aktuellen privaten Datenbank-Cutovers), Frontend V2, Review, Arena, Curation, Playground, LoRA-/Promptkatalog und native ComfyUI-Generierung.

Der Generator wurde jüngst überarbeitet und ist im Code angebunden. Der Katalog-/Datenbankumbau ist **noch in der Entwicklung/Abnahme**: Die Migrationen und Normalisierungswerkzeuge sind implementiert, aber die private, echte Normalisierung und der produktive Cutover sind mit dem öffentlichen Repository nicht als abgeschlossen nachgewiesen. Siehe [aktueller Arbeitsstand](ACTIVE_WORK.md).

## POCs sind Werkzeuge, keine schon beschlossenen Features

Am Card Battler wird derzeit aktiv gearbeitet. Im ComfyReview-Code befinden sich unter anderem deterministische Karten-/Trait-Algorithmen, Modelladapter und Visual-Prompt-Projektion; die spielerseitige Gesamtintegration ist **noch kein fertiges Produkt**. [POC-Status](pocs/card-battler.md).

Weitere Versuche außerhalb dieser Codebasis können parallel stattfinden. Nicht hier enthaltene Experimente werden **nicht** als bereits implementierter ComfyReview-Code ausgegeben und ohne konkreten Dokumentationsbedarf nicht zur verbindlichen Architektur erklärt.

## Frühere Character-Chronicles-Implementierung

Es gab bereits einen **früheren Character-Chronicles-Entwicklungsstand**, dessen Richtung verworfen wurde. Die importierten Konzepttexte enthalten Anklänge daran (z. B. Vite/TypeScript, Chronicle-Events, M6 und Schema 47–58). **Diesen verworfenen technischen Ansatz übernehmen wir nicht automatisch.** Der frühere Code ist **in der inzwischen bereitgestellten
`CharacterChronicle.zip` tatsächlich vorhanden** und wurde unabhängig
vom aktuellen ComfyReview-Code [statisch untersucht](character-chronicles/HISTORICAL_CODE_AUDIT.md).
Darin gab es unter anderem eine Vite-/TypeScript-UI, Campaign-/Trial-
und M6-Services, Worker-Prozessrollen und SQLite-Schema v58.
Die damaligen Abnahmeprotokolle lassen den vollständigen
M6-Zwei-Zyklen-Spielerbeweis **weiterhin offen**.

Das ist ein historischer Beleg – **kein** Argument, diese verworfene
technische Architektur wieder einzuführen. Das Archiv ist nicht Teil
der aktuellen ComfyReview-Runtime und enthält keine nachprüfbare private
Live-Datenbank.

Das Verwerfen einer Architektur bedeutet **nicht**, dass alle überlegten Spielideen, Geschichten, Regeln oder Mechaniken ungültig sind. Wir bewahren sie als Quellenmaterial, aber unterscheiden bewusst zwischen **inhaltlich interessant** und **technisch bindend**.

## Wie eine Idee zur Entscheidung wird

Siehe [Entscheidungs- und Herkunftsregeln](DECISION_POLICY.md). Nur wenn eine Entscheidung ausdrücklich für den **aktuellen Arbeitskontext** bestätigt und am bestehenden Code/POC geprüft wurde, ist sie eine technische Vorgabe. Eine Formulierung wie „verbindlich“, „DECIDED“, „Baseline abgeschlossen“ oder „Schema 58“ in einem übernommenen Dokument macht sie **nicht automatisch** zur neuen Zielarchitektur.

[Chronicles-Konzeptsammlung](character-chronicles/README.md) · [ComfyReview-Arbeitsstand](ACTIVE_WORK.md) · [Offene Entscheidungen](OPEN_DECISIONS.md)
