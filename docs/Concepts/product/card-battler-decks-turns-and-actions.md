# Card Battler – Decks, Züge und Ausspielhandlungen

Dokumentrolle: fachlicher MVP-Produktvertrag für Deckzusammensetzung und den
grundlegenden Zugablauf des Card Battlers

Autorität: autoritativer Zielvertrag für aktive Deckgröße, gespeicherte Decks,
reguläres Ziehen, Zugphasen und normale Kartenausspielungen

Rules-Version: `card_battler_rules_v0.1`

Status: **Baseline abgeschlossen**

Stand: 10. September 2026

## Zweck und Begriffe

Dieses Dokument ergänzt den Spielfeld- und Kampfvertrag um die erste
verbindliche Makrostruktur eines Matches.

- Ein **Zug** ist der vollständige Spielablauf genau eines Spielers.
- Eine **Runde** ist abgeschlossen, nachdem beide Spieler je einen Zug hatten.
- Eine **Ausspielhandlung** ist das freiwillige Spielen genau einer Karte aus
  der Hand in einen zulässigen freien Feldslot.

Die Formulierung „eine Karte pro Runde ziehen“ wird für den TCG-Ablauf als
**eine reguläre Karte zu Beginn jedes eigenen Zuges** präzisiert. Dadurch ziehen
beide Parteien innerhalb einer vollständigen Runde grundsätzlich je eine
Karte, soweit kein Effekt davon abweicht. Das gilt auch für den ersten Zug des
Erstspielers.

## Sammlung und aktive Decks

Die persönliche Kartensammlung darf mehr als 40 Karten enthalten. Ein Spieler
darf aus dieser Sammlung mehrere benannte Decklisten anlegen und pflegen.

Ein für ein Match gewähltes aktives Deck enthält **exakt 40 Karten**. Weniger
oder mehr als 40 Karten erfüllen die Deck-Readiness nicht. Sammlung und
Deckliste sind deshalb getrennte Projektionen: Der Besitz einer Karte nimmt sie
nicht automatisch in jedes Deck auf.

Mehrere gespeicherte Decklisten dürfen dieselbe besessene `CardIdentity`
referenzieren. Eine Deckliste ist keine zweite Kartenkopie und verändert weder
Kartenentwicklung noch Bild-, Champion-, Availability- oder
Delete-or-Live-Zustand. Zu Matchbeginn friert der Server die gewählte
Deckrevision zusammen mit den verwendeten Kartenrevisionen und der
`RulesVersion` als reproduzierbaren Match-Snapshot ein.

Innerhalb derselben Deckrevision darf jede `CardIdentity` genau einmal
vorkommen. Die 40 Einträge bilden eine Menge einzigartiger Kartenidentitäten;
ein Mengenfeld mit Anzahl größer eins existiert nicht. Auch bildlose
Standardkarten sind getrennte einzigartige CardIdentities. Verschiedene Karten
dürfen zufällig ähnliche Werte oder Traits besitzen, sind dadurch aber keine
Kopien. Weder Sammlung noch Effekte erzeugen Kartendopplungen oder Tokens.

v0.1 besitzt kein Side-/Reserve-Deck. Wird das gebundene Bild einer CardIdentity
zwischen Deckbau und Matchstart endgültig gelöscht, bleibt dieselbe
CardIdentity in der Deckrevision und fällt atomar auf ihr ursprüngliches
bildloses Standardprofil zurück. Deck-Readiness wird neu projiziert; es wird
weder eine fremde Ersatzkarte eingesetzt noch die Identität aus dem Deck
entfernt. Ein bereits gestartetes Match verwendet weiterhin seinen
eingefrorenen Snapshot.

## Matchbeginn und Einsatzverzögerung

Nach der serverseitigen Bestimmung des Erstspielers werden beide 40-Karten-
Decks reproduzierbar gemischt. Jeder Spieler zieht anschließend genau **fünf
Karten** als Starthand. Das Ziehen der Starthand ist kein regulärer Ziehvorgang
und löst keine Effekte aus, die auf die Ziehphase oder auf reguläres Ziehen
reagieren.

Der Erstspieler zieht in der Ziehphase seines ersten Zuges regulär eine Karte.
Er darf in diesem Zug jedoch keinen normalen Angriff erklären. Die
Angriffsphase bleibt als Timingphase bestehen und kann durchlaufen werden,
damit der Phasenablauf und ausdrücklich phasengebundene Effekte stabil bleiben.

Jede Figurenkarte erhält beim Betreten des Feldes Einsatzverzögerung. Sie darf
bis zum Beginn des nächsten eigenen Zuges ihres Controllers keinen normalen
Angriff erklären. Das gilt sowohl für eine normal aus der Hand gespielte als
auch für eine durch einen Effekt direkt aufs Feld gebrachte Karte.
Einsatzverzögerung verhindert weder Verteidigung noch allein aufgrund dieses
Status die Verwendung ihrer zulässigen Fähigkeiten. Nur eine ausdrückliche,
strukturierte Kartenregel wie `grant_immediate_attack` darf die Verzögerung
für den angegebenen Umfang umgehen.

Vor dem Mischen bestimmt der Server zufällig einen Initiativgewinner. Dieser
wählt verbindlich, welcher Spieler beginnt. Nachdem beide Starthände gezogen
sind und der Startspieler bekannt ist, darf jeder Spieler genau einmal privat
zwischen null und fünf Karten zum Austausch markieren. Beide Entscheidungen
werden zunächst gebunden. Anschließend werden die markierten Karten beiseite
gelegt, dieselbe Anzahl aus dem verbleibenden Deck gezogen und erst danach die
beiseitegelegten Karten zurückgemischt. Der Austausch ist kein reguläres
Ziehen, Abwerfen oder Zurücklegen und löst keine entsprechenden Karteneffekte
aus.

## Verbindlicher Zugablauf

Jeder Zug besteht in dieser Reihenfolge aus sechs Phasen:

1. **Start-/Refresh-Phase** – zuggebundene Zustände und Nutzungen werden
   aktualisiert.
2. **Ziehphase** – der aktive Spieler zieht regulär genau eine Karte.
3. **Hauptphase I** – Karten dürfen vor dem Angriff ausgespielt und zulässige
   Fähigkeiten verwendet werden.
4. **Angriffsphase** – zulässige eigene Figurenkarten dürfen nach den Linien-
   und Kampfregeln angreifen.
5. **Hauptphase II** – Karten dürfen nach der Angriffsphase ausgespielt und
   zulässige Fähigkeiten verwendet werden.
6. **Endphase** – End-of-turn-Effekte, Ablaufzeiten und der Spielerwechsel
   werden abgewickelt.

Ohne einen ausdrücklichen Karteneffekt oder eine andere versionierte Regel gilt:

- In Hauptphase I sind höchstens **zwei normale Ausspielhandlungen** erlaubt.
- In Hauptphase II sind erneut höchstens **zwei normale Ausspielhandlungen**
  erlaubt.
- Beide Limits sind voneinander unabhängig. Ungenutzte Ausspielhandlungen aus
  Hauptphase I werden nicht in Hauptphase II übertragen.
- Damit sind regulär höchstens vier Karten pro eigenem Zug ausspielbar.
- Die Angriffsphase darf auch ohne Angriff beendet werden; Hauptphase II bleibt
  dann trotzdem erreichbar.

## Was eine Ausspielhandlung verbraucht

Eine normale Ausspielhandlung wird genau dann verbraucht, wenn der aktive
Spieler eine Karte freiwillig aus seiner Hand auf einen regulären Feldslot
spielt.

Das Ausspielen einer höher entwickelten Karte verbraucht ebenfalls genau **eine**
Ausspielhandlung. Ihre Präsenzvoraussetzung wird zuerst geprüft; anschließend
geforderte Opfer sind Kosten dieser Ausspielung und keine zusätzlichen
Ausspielhandlungen. Die geopferten Karten gelten nicht als im Kampf zerstört.

Für sich allein verbrauchen folgende Vorgänge keine normale
Ausspielhandlung:

- das Aufdecken einer bereits liegenden Karte,
- der Wechsel zwischen Angriffs- und Verteidigungsmodus,
- eine zulässige Bewegung einer bereits liegenden Karte,
- die Aktivierung oder Auflösung einer Fähigkeit,
- das Opfern, Zerstören oder Entfernen einer bereits liegenden Karte,
- das Zurücknehmen einer Karte auf die Hand,
- sowie eine durch einen Effekt direkt aufs Feld gebrachte Karte.

Diese Vorgänge sind dadurch nicht automatisch erlaubt oder unbegrenzt. Ihre
eigenen Timing-, Nutzungs- und Kostenregeln bleiben maßgeblich.

Freiwillige Modus-, Reveal- und Slotwechsel folgen der einmaligen
Formationsaktion im
[`Spielfeld- und Kampfvertrag`](card-battler-board-and-combat-foundation.md).

Ein Effekt darf die Phasenlimits nur verändern oder umgehen, wenn seine
serverseitig materialisierte Regel dies ausdrücklich tut, beispielsweise über
ein registriertes `modify_deploy_limit` oder `effect_deploy`. Ein bloßer
Beschreibungstext der LLM kann kein zusätzliches Ausspielen erlauben.

## Ressourcen, Handlimit und Matchende

Der Battler besitzt keine allgemeine Mana-, Energie- oder Landressource.
Normales Ausspielen verwendet die festgelegte Feldpräsenz- und Opferlogik.
Fähigkeiten dürfen ausschließlich ihre eigenen registrierten Kosten verwenden,
beispielsweise Lebenspunkte, Handkarten, Opfer, Erschöpfung oder begrenzte
Nutzungen. Die LLM darf keine weitere Ressource erfinden.

Das reguläre Handlimit beträgt **sieben Karten**. Nach der Auflösung aller
Endphaseneffekte muss der aktive Spieler überzählige Karten seiner Wahl
abwerfen, bis sieben verbleiben. Effekte dürfen ein anderes temporäres
Handlimit ausdrücklich materialisieren.

Ein Spieler verliert das Match, wenn mindestens eine dieser Bedingungen
eintritt:

- seine Lebenspunkte fallen auf null oder darunter,
- er kann einen verpflichtenden Ziehvorgang nicht vollständig erfüllen,
- oder er gibt das Match auf.

Ein leeres Deck allein ist noch keine Niederlage; entscheidend ist der
gescheiterte verpflichtende Ziehvorgang. Nach jeder atomaren Systemaktion und
jedem vollständig aufgelösten Kettenglied prüft der Server das Matchende, bevor
ein weiteres Kettenglied oder Reaktionsfenster beginnt. Erfüllen beide Parteien
durch dasselbe atomare Ereignis gleichzeitig eine Niederlagebedingung, endet
das Match unentschieden. Der Endphasen-Discard erfolgt als eine atomare Aktion;
seine Trigger entstehen erst danach und vor der erneuten Handlimitprüfung.

## Serverseitiger Minimalzustand

Der autoritative Matchzustand führt mindestens:

```text
active_player_id
round_number
turn_number
phase
normal_draw_completed
main_1_deployments_used
main_2_deployments_used
selected_deck_revision_id
frozen_card_revision_ids
rules_version
first_player_id
opening_hand_drawn
first_turn_attack_lock
initiative_winner_id
mulligan_state
hand_limit
life_points_by_player
match_result
```

Jede Feldkarte führt außerdem den für Einsatzverzögerung maßgeblichen
Eintrittszug beziehungsweise einen daraus eindeutig ableitbaren
`attack_eligible`-Zustand.

Der Server validiert Ziehen, Phasenwechsel, Ausspielhandlung,
Präsenzvoraussetzung, Opferzahlung, Slotbelegung und Effektausnahmen. Browser
und LLM dürfen diese Regeln nur darstellen beziehungsweise sprachlich
erläutern.

## Verbindliche Invarianten

1. Ein matchbereites aktives Deck besitzt exakt 40 Karten.
2. Die Sammlung darf größer sein und mehrere Decklisten speisen.
3. Ohne ausdrückliche Ausnahme zieht jeder Spieler einmal zu Beginn seines
   eigenen Zuges.
4. Hauptphase I und Hauptphase II besitzen jeweils ein eigenes Limit von zwei
   normalen Ausspielhandlungen.
5. Nicht genutzte Ausspielhandlungen aus Hauptphase I werden nicht übertragen.
6. Eine hochstufige Karte samt ihrer Opferzahlung verbraucht genau eine normale
   Ausspielhandlung.
7. Opfer, Fähigkeiten und Zustandsänderungen bereits liegender Karten sind
   nicht allein deshalb weitere Ausspielhandlungen.
8. Nur strukturierte, serverautorisierte Effekte dürfen Zieh- oder
   Ausspiellimits verändern beziehungsweise umgehen.
9. Ein Match bleibt durch eingefrorene Deck-, Karten- und Rules-Versionen
   reproduzierbar.
10. Beide Spieler beginnen mit genau fünf Handkarten.
11. Der Erstspieler zieht in seinem ersten Zug regulär, darf in diesem Zug aber
    keinen normalen Angriff erklären.
12. Jede neu aufs Feld gekommene Figur darf grundsätzlich erst ab dem Beginn
    des nächsten eigenen Zuges ihres Controllers normal angreifen.
13. Einsatzverzögerung verbietet nicht automatisch Verteidigung oder
    Fähigkeiten und wird nur durch eine ausdrückliche strukturierte Regel
    umgangen.
14. Der zufällig bestimmte Initiativgewinner wählt den Erstspieler.
15. Jeder Spieler darf einmalig null bis fünf Starthandkarten austauschen,
    ohne Draw-, Discard- oder Return-Trigger auszulösen.
16. Es existiert keine allgemeine Mana- oder Energieressource.
17. Das Handlimit beträgt in der Endphase grundsätzlich sieben Karten.
18. Null Lebenspunkte, ein nicht erfüllbarer Pflichtzug oder Aufgabe erzeugen
    eine Niederlage; ein bloß leeres Deck nicht.
19. Ein gemeinsames atomares Ereignis, das beide Parteien verlieren lässt,
    erzeugt ein Unentschieden.
20. v0.1 besitzt kein Side-/Reserve-Deck.
21. Eine gelöschte Bildbindung setzt dieselbe CardIdentity vor dem nächsten
    Match auf ihr ursprüngliches Standardprofil zurück; laufende Matches
    behalten ihren Snapshot.
22. Matchende wird nach jeder atomaren Systemaktion und jedem vollständig
    aufgelösten Kettenglied vor der nächsten Interaktion geprüft.

## Post-v0.1-Erweiterungen

Side-/Reserve-Decks, Best-of-Serien und andere Deckformate benötigen eine neue
Rules-Version. Sie sind keine offenen Punkte der Baseline v0.1. Command-,
Snapshot-, Resume- und Persistenzgrenzen stehen in der
[`Card-Battler-Runtime-Architektur`](card-battler-runtime-architecture.md).

Spielfeld, Linien und normale Kampfauflösung stehen in
[`card-battler-board-and-combat-foundation.md`](card-battler-board-and-combat-foundation.md).
Effektformen, Reaktionsketten und LLM-Abgrenzung stehen in
[`card-battler-effect-grammar-and-llm-authoring.md`](card-battler-effect-grammar-and-llm-authoring.md).
Friedhof, Endphasen-Discard, Active-player-Pflichttrigger und ausführbare
Opcodes stehen in
[`card-battler-zones-statuses-and-opcode-registry.md`](card-battler-zones-statuses-and-opcode-registry.md).
Kartenentstehung und Entwicklung stehen in
[`card-crafting-and-playground-combination-lifecycle.md`](card-crafting-and-playground-combination-lifecycle.md).
