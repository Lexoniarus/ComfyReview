# Social Network – Plattform mit Charakter-Chats

**Dokumentklasse:** `WORKING_VISION` · **Entwicklungsorientierung:** nach dem Card Battler und einem ersten [Timeline-Slice](timeline.md), vor Storyline und VN-Content · **Status in ComfyReview:** Zielidee, kein integriertes Gesamtsystem.

## Fachliche Absicht

Die Figuren sollen eine **soziale Präsenz** erhalten, mit der Spielende interagieren können. Nach einem zunächst begrenzten [Timeline-Slice](timeline.md) ist das **breitere Social Network mit Chat-Interaktion** der nächste Entwicklungsschwerpunkt: Charakter-Chats und weitere Plattformfunktionen bauen auf dem Timeline-Kontext auf beziehungsweise verzahnen sich mit ihm. Ob die beiden Schwerpunkte technisch oder als Releases getrennt bleiben, ist **nicht entschieden**. So werden erste soziale und erzählerische Kontakte möglich, ohne bereits aufwendig zusammengesetzte VN-Szenen vorauszusetzen.

Dieses Social Network soll später Platz für die übergreifende Welt und den Academy-/Schuljahreskontext bieten. Wie Post-/Reaktionsmodelle, Nachrichten, Zustandsübergänge, KI-Unterstützung und Beziehungen im Detail aussehen, muss erst erprobt werden.

## Soziales Schlussfolgern: Ereignis, Wissen, Annahme und Gerücht

Das soziale Spielerlebnis soll über das Lesen eines Feeds und das Austauschen
von Nachrichten hinausgehen. **Unterschiedliche Figuren können dasselbe
Ereignis unterschiedlich wahrnehmen, nur Teile davon kennen oder falsche
Schlüsse daraus ziehen.** Öffentliche Posts, private Nachrichten,
persönliche Einschätzungen und Gerüchte können sich widersprechen. Für
Spielende kann daraus die Möglichkeit entstehen, Perspektiven zu vergleichen,
gezielt nachzufragen und Informationen selbst einzuordnen.

Als **fachliche Leitidee** sollen mindestens folgende Ebenen auseinander-
gehalten werden: **was tatsächlich passiert ist**, **wer davon weiß**,
**was eine Figur glaubt oder vermutet** und **was öffentlich beziehungsweise
privat kommuniziert wurde**. Ein Gerücht ist deshalb nicht automatisch
Weltwahrheit, ein öffentlicher Post nicht die vollständige Sicht seines
Autors und eine Charakterantwort nicht automatisch geteiltes Wissen aller
anderen Figuren.

Soziale Entscheidungen könnten später Beziehungen, Vertrauen und
[Storysituationen](storyline.md) beeinflussen; umgekehrt können Ereignisse
aus dem [Card Battler](card-battler.md) oder anderen Spielbereichen
Gesprächsanlässe schaffen. **Wie** Informationen entstehen, weitergegeben,
korrigiert, erinnert oder für Spielregeln ausgewertet werden, ist **noch
offen**. Insbesondere werden dadurch weder ein bestimmtes
Wissens-/Gerüchte-Schema noch eine LLM-/RAG-Architektur oder verbindliche
Relationship-Werte beschlossen.

Ein KI-generierter Chattext darf nicht allein durch seine Formulierung
neue kanonische Tatsachen oder Spielwirkungen festschreiben. Ebenso
sollen private Gespräche nicht ohne einen dafür zugelassenen Weg anderen
Figuren als bekannt unterstellt werden. Das sind **fachliche Grenzen
für spätere POCs**, keine Behauptung über bereits vorhandene
Social-/Story-Services im aktuellen ComfyReview.

## Abgrenzung

- Eine **Chat-Oberfläche** ist Teil des künftigen Spielerlebnisses, aber derzeit **nicht** als vollständige Funktion im geprüften ComfyReview-Webfrontend nachgewiesen.
- Diese Zielbeschreibung setzt **keine** konkrete LLM-/RAG-/Providerarchitektur und **keinen** Chat-Datenbankvertrag fest.
- Alte Network-/Social-Vorgaben aus [importierten Quelltexten](../sources/README.md) sind **Ideen und historische Lösungen**, keine automatisch geltenden Spezifikationen.
- Der visuelle VN-Szenenrenderer ist **keine Voraussetzung** dafür, dass Timeline und Chat als Interaktionssysteme sinnvoll funktionieren.

**Nächster Entwicklungsbereich:** [Storyline](storyline.md). [Academy/Schuljahr](academy-and-world.md) ist ein möglicher Welt- und Fortschrittskontext dieser Storyline, **keine zusätzlich beschlossene eigenständige Pflichtphase**. Die technische Umsetzung kann sich mit Social/Chat überlappen, ohne die grobe Orientierung zu einem starren Releaseplan zu machen.
