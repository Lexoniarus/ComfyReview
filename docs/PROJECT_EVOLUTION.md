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

## Gewonnene Reihenfolge aus den bisherigen Versuchen

**Entwicklungsorientierung vom 2026-10-09, kein starrer Meilensteinplan:**
Die Ideen für Card Battler, Worldbuilding, Academy und Character Chronicles
haben erst im Laufe der Versuche zu einem zusammenhängenden Produktbild
gefunden. Der frühere Chronicle-Ansatz ging mit umfangreicher Architektur,
Spiel- und VN-Organisation voraus, bevor die heute wichtigeren spielerischen
Grundlagen hinreichend geklärt waren. Das ist eine Erkenntnis über die
**sinnvolle Reihenfolge** – kein Urteil, dass sämtliche früheren Ideen
wertlos oder sämtliche damaligen POCs gescheitert seien.

1. **Card Battler – aktuelle Priorität.** Im vorhandenen ComfyReview-Code
   zuerst die Card-Battler-Funktionen über isolierte Algorithmen hinaus in
   Richtung eines tatsächlich funktionierenden, testbaren Spielkerns
   entwickeln. Der aktuelle [POC](pocs/card-battler.md) liefert Belege, nicht
   bereits die endgültigen Spielregeln oder UI-Verträge.
2. **Social Network – nächste größere Produktschicht.** Eine Timeline und
   eine Chat-Oberfläche für Interaktionen mit den Charakteren geben diesen
   eine soziale Präsenz, bevor eine vollständige VN-Szenenbühne existiert.
   Technische Umsetzung, Datenmodell und Detailumfang bleiben offen.
3. **Academy / Schuljahr – dazwischen aufbauen.** Schuljahresstruktur,
   Figurenentwicklung, Beziehungen und Fortschritt verbinden die zuvor
   entwickelten Spiel- und Sozialfunktionen zu einem fortlaufenden
   Welt-/Spielkontext. Die genaue zeitliche Verzahnung **mit** dem Social
   Network muss nicht bereits als eigene Phase feststehen.
4. **Visuelle VN – bewusst zuletzt.** Erst nach tragfähigen
   Spiel-/Interaktions-/Schuljahressystemen wird die aufwendige szenische
   Präsentation zum Gesamterlebnis ausgebaut. Insbesondere
   **Freistellung, Segmentierung/Matting und das konsistente
   Zusammensetzen visueller Szenelemente** sind deutlich riskanter als
   reine Timeline- oder Chat-Oberflächen. Diese technischen Probleme
   dürfen durch **kleine frühere Feasibility-POCs** untersucht werden;
   das macht die vollständige VN aber **nicht** zum nächsten
   Implementierungsschritt.

Diese Reihenfolge ist eine **begründete Arbeitsrichtung und Abhängigkeit**,
kein bereits bestätigter MVP-Zuschnitt, keine Verpflichtung auf vier
Projektphasen und keine Übernahme früherer Schema-/Guardian-/Frontend-
Verträge. Die Ergebnisse jedes POCs können Umfang und Übergänge verändern.

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
