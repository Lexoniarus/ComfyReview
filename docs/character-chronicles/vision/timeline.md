# Timeline – nächster begrenzter Entwicklungsfokus

**Dokumentklasse:** `WORKING_VISION` · **Reihenfolge:** nach dem Card-Battler-Schwerpunkt, vor dem umfassenderen Social Network mit Chat · **Status in ComfyReview:** nicht als integrierte Spielerfunktion nachgewiesen.

## Fachliche Absicht

Die **Timeline** soll Figuren, Beiträge, Ereignisse und Reaktionen der
[bestätigten Kobe-/Academy-Welt](world.md) zunächst über eine
verständliche, zeitlich oder sozial geordnete Oberfläche erfahrbar
machen. Sie ist ein **eigener erprobbarer Entwicklungsschwerpunkt**, aber
damit **weder schon eine separat beschlossene App noch automatisch eine
vollständige Social-Network-Architektur**. Ob und welche Posts, Profile oder
anderen Aktionen in der ersten Version erforderlich sind, bleibt offen.

Der erste Timeline-Slice darf bewusst klein sein, um Benutzerführung,
Datenherkunft und echte Interaktionen zu testen, bevor die breitere
[Social-Network-Plattform mit Charakter-Chats](social-network.md) folgt.
Die Implementierungsarbeiten dürfen dabei technisch überlappen.

## Grenzen und offene Fragen

- **Noch kein IST-Feature:** Das geprüfte ComfyReview enthält keinen
  fertigen Timeline-Flow. [Aktueller Code- und Arbeitsstand](../../ACTIVE_WORK.md).
- **Keine fixierte Feed- oder Backend-Architektur:** Speicherung,
  Reaktionen, Moderation, Generierung, Figurenprofile und UI werden durch
  POCs und bewusste Entscheidungen abgegrenzt.
- **Keine stillschweigende Academy- oder Story-Gate-Übernahme:**
  Historische Schuljahreskalender, Character-Events und alte
  `ChronicleRun`-Schemata sind [Quellenmaterial](../sources/README.md),
  keine jetzigen Anforderungen.
- **Nicht VN-Content:** Ein zeitlicher/szenischer Kontext ist noch keine
  Visual-Novel-Szene; die eigentliche [VN-Content-Entwicklung](visual-novel.md)
  folgt zuletzt.

**Nächster Schritt:** fachlichen Minimalumfang, aktive Spieleraktionen
und beobachtbare POC-Abnahme festlegen; erst danach eine verbindliche
Implementierungsspezifikation erstellen.
[Entwicklungsorientierung](../../PROJECT_EVOLUTION.md) ·
[Offene Entscheidungen](../../OPEN_DECISIONS.md).
