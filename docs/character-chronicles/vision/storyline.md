# Storyline – Erzählsystem nach Social/Chat

**Dokumentklasse:** `WORKING_VISION` · **Reihenfolge:** nach Timeline und Social Network mit Charakter-Chats, vor der eigentlichen VN-Content-Entwicklung · **Status in ComfyReview:** fachliche Zukunftsidee, keine integrierte Story-Runtime.

## Fachliche Absicht

Die **Storyline** soll aus Figuren, Entscheidungen, Ereignissen,
Beziehungen und Fortschritt eine nachvollziehbare fortlaufende Erzählung
formen. Dafür können später sowohl der
[Card Battler](card-battler.md) als auch
[Timeline](timeline.md) und [Social Network/Chat](social-network.md)
Anknüpfungspunkte liefern. **Diese Zusammenhänge sind Zielideen,
noch keine technisch entschiedenen Domain- oder Eventverträge.**

Ein **späterer fachlicher Meilenstein** schützt dabei die
[Konsistenz der Spielwelt gegenüber der technischen Bildproduktion](README.md#späterer-fachlicher-meilenstein-spielwelt-und-bildproduktion):
Ein Bild, das durch neue Prompts oder besseres Rendering anders
aussieht, verändert nicht ohne ein dafür vorgesehenes
Storyereignis automatisch die Figur oder ihre Vergangenheit.
Wie dieser Schutz umgesetzt wird, bleibt offen.

## Zwei Academy-Jahre sind Weltziel, keine zusätzliche Technikphase

[Academy, Schuljahr und Worldbuilding](academy-and-world.md) sind
**fester Teil der bestätigten Zielwelt**: Der Protagonist erlebt
ab 2032 zwei postsekundäre Academy-Jahre in Kobe, mit Beziehungen,
Freundschaften, Entscheidungen, Alltag und Zukunftsperspektiven.
Die **Visual Novel mit Dating-Sim-Elementen** ist der langfristige
emotionale Kern des Gesamtspiels. Dass wir den Card Battler zuerst
und den eigentlichen VN-Content zuletzt entwickeln, ändert daran nichts.

Daraus folgt **keine** zusätzliche technische Academy-Pflichtphase.
Die alten exakten DayInstance-, Character-State-, Relationship-,
Quest-, Guardian- und Schema-Verträge sind nicht übernommen;
ihre passende Ausgestaltung wird über POCs erneut geprüft.
[Bestätigte Weltbeschreibung](world.md).

## Deutliche Abgrenzung zur Visual Novel

- **Storyline:** Was passiert, welche Figuren sind beteiligt, welche
  Entscheidungen und Konsequenzen werden benötigt? Fachliches Konzept und
  künftige Logik, nicht automatisch ein vollständig implementierter Storygraph.
- **[Visual-Novel-Content](visual-novel.md):** Wie wird die Story
  später mit Figurenbildern, Szenen und eigentlichen VN-Inhalten präsentiert?
  **Diese Content-Entwicklung kommt zuletzt.**
- Kleine frühere technische Untersuchungen zu Story-Schnittstellen oder
  visuellen Assets können sinnvoll sein; sie genehmigen
  **keinen vorgezogenen vollständigen VN-Content-Ausbau**.

**Offen:** Story/Run-Datenmodell, Ereignisregeln, Content-Autorenschaft,
Speicherdauer, dramaturgische Struktur, Academy-Umfang und UI. Historische
Quellen nicht ohne ausdrückliche erneute Entscheidung übernehmen.
[Projektentwicklung](../../PROJECT_EVOLUTION.md) ·
[Offene Entscheidungen](../../OPEN_DECISIONS.md).
