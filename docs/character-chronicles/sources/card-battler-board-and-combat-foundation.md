# Card Battler – Spielfeld, Linien und verdeckte Karten

> **DOKUMENTSTATUS: SOURCE_MATERIAL – NICHT VERBINDLICH.** Vollständige importierte Quellenfassung vom 2026-10-09. **Nicht** der aktuelle Code-Ist-Zustand, **kein** genehmigter Implementierungsplan und **keine** verbindliche Character-Chronicles-Architektur. Frühere Angaben wie „Autorität“, „DECIDED“, „Baseline abgeschlossen“ und „implementiert“ sind **historischer Originalwortlaut**.

**Quellkategorie:** `MECHANICS_CANDIDATE`  
**Worum es geht:** Fünf-Slot-Spielfeld, Linien, Angriff und verdeckte Karten als konkrete historische Regelvariante.  
**Aktueller Referenzpunkt:** [bereinigter Überblick](../vision/card-battler.md) · [Quellenindex](README.md) · [Entscheidungsregeln](../../DECISION_POLICY.md).

## Übernommene Quellenfassung (historischer Entwurf, keine aktuellen Beschlüsse)

**Ab hier folgt der damalige Text einschließlich seiner früheren Status- und Architekturbehauptungen.** Diese dürfen nicht ohne neue Codeprüfung/ausdrückliche Entscheidung in aktive Arbeitsaufträge umgedeutet werden.

---

Dokumentrolle: fachlicher MVP-Produktvertrag für den ersten verbindlichen
Card-Battler-Kern

Autorität: autoritativer Zielvertrag für Spielfeldgeometrie, Slotfreiheit,
Angriffslinien, Sichtbarkeitszustand und grundlegende Angriffsauflösung

Rules-Version: `card_battler_rules_v0.1`

Status: **Baseline abgeschlossen**

Stand: 10. September 2026

## Zweck und Abgrenzung

Dieses Dokument legt den ersten spielmechanischen Card-Battler-Vertrag fest.
Der Battler orientiert sich an klassischen TCGs wie Magic: The Gathering und
Yu-Gi-Oh!, verwendet aber ein eigenes versetztes Fünf-Slot-Feld mit drei
Angriffslinien.

Bereits entschieden sind:

- zwei vordere und drei hintere universelle Kartenslots pro Spieler,
- offene und verdeckte Karten in jedem Slot,
- drei durch die Formation bestimmte Angriffslinien,
- die gemeinsame Sicherung der mittleren Linie durch beide Frontslots,
- die Angriffslinien der fünf eigenen Slots und eine normale Attacke je Figur,
- sowie die Reihenfolge aus Frontverteidigung, hinterem Slot und direktem
  Lebenspunkteangriff.

Die Baseline v0.1 besitzt kein Side-/Reserve-Deck, keine Affinitäten und keine
zusätzlichen Siegbedingungen. Die genaue Verteilung traitloser
Standard-Kampfprofile ist versionierter Base-Deck-Content und wird im
Balance-Playtest kalibriert, ohne die Feldregeln zu öffnen. Präsenz-/Opferkurve,
Effektbudget, Stacking, Kartenzonen und initialer Opcodekatalog sind getrennt
verbindlich definiert.

Kartenentstehung, Playground-Kombinationsbindung, Augments, Verfall, bildloses
Base Deck und Entwicklung bis Legendary stehen getrennt in
[`card-crafting-and-playground-combination-lifecycle.md`](card-crafting-and-playground-combination-lifecycle.md).
Effektformen und ihre LLM-gestützte Materialisierung stehen in
[`card-battler-effect-grammar-and-llm-authoring.md`](card-battler-effect-grammar-and-llm-authoring.md).
Friedhof, Statuszustände und ausführbare Opcodes stehen in
[`card-battler-zones-statuses-and-opcode-registry.md`](card-battler-zones-statuses-and-opcode-registry.md).
Deckgröße, Zugphasen, Ziehen und Ausspiellimits stehen in
[`card-battler-decks-turns-and-actions.md`](card-battler-decks-turns-and-actions.md).

## Universelles Fünf-Slot-Feld

Jeder Spieler besitzt genau fünf reguläre Feldslots:

```text
                   Gegnerische Lebenspunkte

          [Hinten L] [Hinten M] [Hinten R]
               [Vorne L] [Vorne R]

               [Vorne L] [Vorne R]
          [Hinten L] [Hinten M] [Hinten R]

                    Eigene Lebenspunkte
```

Die stabilen Slotrollen lauten:

```text
front_left
front_right
rear_left
rear_center
rear_right
```

Jede spielbare Karte ist strukturell eine Figurenkarte und darf grundsätzlich
in jeden freien Slot gespielt werden. Sie besitzt Angriffs- und
Verteidigungswert. Slot, offene oder verdeckte Lage, Angriffs- oder
Verteidigungsmodus und Kartenregeln bestimmen anschließend ihre zulässigen
Aktionen und Wirkungen. Es existieren keine getrennten Feldzonen für Zauber,
Fallen, Support oder Ausrüstung, weil dies Fähigkeitsfamilien eines Brandings
und keine eigenen Kartenarten sind.

Position, Sichtbarkeit, Kampfmodus und Fähigkeitsfamilie sind getrennte
Regelachsen. Dieselbe Figurenkarte kann daher beispielsweise verdeckt im
Angriffsmodus auf einen Hinterhalt warten oder offen im Verteidigungsmodus eine
Supportfähigkeit tragen.

## Drei Angriffslinien

Ein normaler Angriff wählt genau eine von drei Linien:

```text
Linke Linie
front_left → rear_left → Lebenspunkte

Mittlere Linie
front_left oder front_right → rear_center → Lebenspunkte

Rechte Linie
front_right → rear_right → Lebenspunkte
```

Damit gilt:

- `front_left` schützt die linke und die mittlere Linie.
- `front_right` schützt die rechte und die mittlere Linie.
- `rear_left` ist der hintere Kartenplatz der linken Linie.
- `rear_center` ist der hintere Kartenplatz der mittleren Linie.
- `rear_right` ist der hintere Kartenplatz der rechten Linie.
- Die mittlere Linie ist absichtlich stärker geschützt als die beiden
  Außenlinien.

## Angriffsberechtigung und Linie des Angreifers

Jede angriffsberechtigte Figurenkarte darf grundsätzlich genau **einen normalen
Angriff pro eigener Angriffsphase** erklären. Ein Effekt darf weitere Angriffe
nur über eine ausdrückliche strukturierte Regel gewähren. Angriffsberechtigt
ist eine Karte ohne solche Ausnahme nur, wenn sie im Angriffsmodus liegt, ihre
Einsatzverzögerung beendet ist und in dieser Angriffsphase noch keinen normalen
Angriff erklärt hat.

Der eigene Slot bestimmt die wählbare Angriffslinie:

```text
front_left   → linke oder mittlere Linie
front_right  → rechte oder mittlere Linie
rear_left    → linke Linie
rear_center  → mittlere Linie
rear_right   → rechte Linie
```

Damit dürfen auch Figuren in hinteren Slots normal angreifen. Eigene
Frontkarten blockieren den Angriff einer eigenen hinteren Figur nicht; die
Zielreihenfolge prüft ausschließlich die gegnerische Formation in der
gewählten Linie.

Eine verdeckte Figur im Angriffsmodus wird bei ihrer eigenen gültigen
Angriffserklärung zuerst aufgedeckt. Ihre Reveal- und Reaktionsfenster werden
aufgelöst; bleibt sie danach angriffsberechtigt auf dem Feld, führt sie den
deklarierten Angriff normal fort. Das Aufdecken des eigenen Angreifers ersetzt
den Angriff also nicht. Diese Regel ist vom Angriff **auf ein verdecktes Ziel**
zu unterscheiden, der weiterhin nach der Aufdeckung des Ziels ohne normalen
Kampf endet.

Einsatzverzögerung und die Erstspieler-Angriffssperre stehen im
[`Deck- und Zugvertrag`](card-battler-decks-turns-and-actions.md).

## Freiwillige Formationsaktion

Jede Figurenkarte, die bereits zu Beginn des aktuellen eigenen Zuges unter der
Kontrolle des Spielers auf dem Feld lag, darf grundsätzlich genau **eine
freiwillige Formationsaktion pro eigenem Zug** ausführen. Sie ist nur in der
eigenen Hauptphase I oder Hauptphase II und außerhalb einer laufenden
Kettenauflösung zulässig.

Eine Formationsaktion wählt genau eine der folgenden Veränderungen:

1. Wechsel zwischen Angriffs- und Verteidigungsmodus,
2. freiwilliges Aufdecken einer verdeckten Karte unter Beibehaltung ihres
   Kampfmodus,
3. Bewegung in einen beliebigen freien regulären Slot der eigenen Formation
   unter Beibehaltung von Sichtbarkeit und Kampfmodus.

Diese Möglichkeiten dürfen nicht innerhalb derselben Formationsaktion
kombiniert werden. Ein freiwilliges Aufdecken eröffnet die zugehörigen
Reveal-/Reaktionsfenster. Eine bereits offene Karte darf ohne ausdrücklichen
Effekt nicht wieder verdeckt werden.

Eine Karte darf keine freiwillige Formationsaktion ausführen, wenn sie erst im
aktuellen Zug das Feld betreten oder bereits in diesem Zug normal angegriffen
hat. Sie darf daher vor ihrem Angriff den Modus wechseln, sich aufdecken oder
bewegen und danach – soweit sonst angriffsberechtigt – noch angreifen. Nach
einem Angriff kann sie in Hauptphase II nicht kostenlos in Verteidigung oder
einen anderen Slot wechseln.

Eine Bewegung setzt weder Einsatzverzögerung noch eine bereits verbrauchte
Attacke oder Nutzung zurück. Sie ist keine Kartenausspielung. Strukturierte
Effekte dürfen zusätzliche oder erzwungene Zustands- und Positionsänderungen
auslösen; diese sind keine freiwillige Formationsaktion, sofern ihre Regel sie
nicht ausdrücklich als solche deklariert.

## Zielreihenfolge eines Angriffs

Nach Wahl der Angriffslinie ermittelt die Simulation das erste gültige Ziel in
dieser Reihenfolge:

1. eine die Linie schützende Frontkarte,
2. nach freier Front den hinteren Slot der gewählten Linie,
3. erst bei vollständig freier Linie die gegnerischen Lebenspunkte.

In der linken und rechten Linie existiert jeweils genau ein zugeordneter
Frontverteidiger. In der mittleren Linie schützen beide Frontslots. Sind dort
beide belegt, wählt der Angreifer bei der Angriffserklärung einen der beiden
gültigen Frontverteidiger und bindet dieses Ziel für den Angriff. Die andere
Frontkarte blockiert die Mitte danach weiterhin. Ein direkter Angriff durch
die Mitte ist erst zulässig, wenn `front_left`, `front_right` und
`rear_center` kein blockierendes Ziel enthalten.

Eine Figurenkarte im zugeordneten hinteren Slot ist nach freier Front das
nächste gültige Kampfziel und verhindert damit den direkten
Lebenspunkteangriff dieser Linie. Zusätzliche Effekte dürfen Zielreihenfolge,
Durchbruch oder Intercept verändern, aber ohne solchen Effekt wird keine
belegte Figurenposition übersprungen.

## Offene und verdeckte Karten

Jede Karte in einem Feldslot besitzt zwei voneinander unabhängige Zustände:

```text
face_up
→ Identität, Werte, Branding und öffentliche Effekte sind sichtbar

face_down
→ Identität, Werte und Branding sind für den Gegner verborgen
→ Aufdeckung durch Angriff, eigenen Reveal oder Karteneffekt

attack
→ Kampf wird mit dem Angriffswert geführt
→ normale eigene Angriffsdeklaration ist nach den späteren Aktionsregeln möglich

defense
→ Kampf wird mit dem Verteidigungswert geführt
→ keine normale eigene Angriffsdeklaration ohne ausdrücklichen Effekt
```

Alle vier Kombinationen aus `face_up | face_down` und `attack | defense` sind
grundsätzlich zulässige Spielzustände. Eine verdeckte Karte im Angriffsmodus
wird spätestens bei ihrer normalen Angriffsdeklaration aufgedeckt. Branding-
Fähigkeiten dürfen frühere, spätere oder reaktive Reveals auslösen. Dadurch
sind Hinterhalte, fallenartige Effekte und echte Bluffs möglich, ohne
typgebundene Feldzonen einzuführen.

Die Simulation besitzt jederzeit die vollständige Kartenidentität. `face_down`
ist eine Visibility Policy gegenüber dem Gegner und Renderer, keine fehlende
Serverinformation. Save, Replay und Debugzustand bleiben vollständig
deterministisch.

## Angriff auf eine verdeckte Karte

Wird eine verdeckte Karte zum ersten gültigen Ziel eines Angriffs, gilt der
Aufdeckangriff:

1. Die Karte wird aufgedeckt.
2. Ihr zuvor gewählter Angriffs- oder Verteidigungsmodus bleibt erhalten und
   wird nun sichtbar.
3. Ihre Reveal-, Hinterhalt- und Reaktionsfenster werden bestimmt und in
   festgelegter Reihenfolge aufgelöst.
4. Der normale Angriff endet danach ohne Angriffs-/Verteidigungswertvergleich,
   ohne unmittelbare Kampfzerstörung und ohne Differenzschaden an
   Lebenspunkten.
5. Soweit kein eigener Karteneffekt etwas anderes bewirkt, bleibt die
   aufgedeckte Karte in ihrem Slot liegen. Erst ein späterer Angriff führt den
   offenen Figurenkampf gegen ihren sichtbaren Kampfmodus.

Das Aufdecken ist damit die vollständige Grundwirkung des ersten Angriffs auf
eine verdeckte Karte und kein bloßer Zwischenschritt desselben Kampfes. Da jede
belegte reguläre Position eine Figurenkarte enthält, schützt ein verdecktes
Ziel die Linie mindestens vor diesem einen normalen Angriff. Fallen-,
Support-, Zauber- und Verteidigungsfähigkeiten dürfen beim Reveal zusätzliche
Wirkungen erzeugen, ersetzen aber diese Grundregel nur mit einem ausdrücklich
registrierten Opcode.

## Offener Kampf nach Angriffs- und Verteidigungsmodus

Ein normaler Angriff kann nur von einer dazu berechtigten Karte im
Angriffsmodus deklariert werden. Eine Karte im Verteidigungsmodus kann ohne
ausdrückliche Fähigkeit nicht angreifen.

Ist das erste gültige Ziel bereits offen, bestimmt dessen Kampfmodus den
verglichenen Wert:

```text
Ziel im Angriffsmodus
→ Angriffswert des Angreifers gegen Angriffswert des Ziels
→ Zielwert niedriger: Ziel wird zerstört; positive Differenz trifft dessen Lebenspunkte
→ Werte gleich: beide Karten werden zerstört; kein Differenzschaden
→ Zielwert höher: Angreifer wird zerstört; positive Differenz trifft dessen Lebenspunkte

Ziel im Verteidigungsmodus
→ Angriffswert des Angreifers gegen Verteidigungswert des Ziels
→ Zielwert niedriger: Ziel wird zerstört; kein Lebenspunkteschaden
→ Werte gleich: beide Karten bleiben liegen; kein Lebenspunkteschaden
→ Zielwert höher: beide Karten bleiben liegen; positive Differenz trifft die Lebenspunkte des Angreifers
```

Damit ist der Verteidigungsmodus der verlässliche Schutz vor
Durchschlagsschaden, verzichtet im Gegenzug aber auf die normale
Angriffsmöglichkeit. Der Angriffsmodus bedroht den Gegner aktiv, setzt den
Spieler bei einer Niederlage im offenen Kampf jedoch dem Differenzschaden aus.

Figurenkarten besitzen keine eigenen Lebenspunkte und speichern keinen
Kampfschaden. Ein Wertevergleich zerstört eine Karte nach den obigen Regeln
oder lässt sie ohne verbleibende Schadensmarke im Slot liegen. Zeitlich
begrenzte Buffs, Debuffs und Zustände werden als `EffectInstance` geführt und
ändern für ihre festgelegte Dauer die berechneten Werte; sie sind kein
persistenter Figurenschaden. Nach Anwendung aller Modifier werden ATK und DEF
mindestens auf null begrenzt.

Der Regelbegriff **Schaden** bezeichnet damit Lebenspunkteschaden. Zerstörung,
Opfer, Entfernung, Werteverlust und Moduswechsel sind eigene Ereignistypen und
lösen nur die jeweils ausdrücklich registrierten Trigger aus.

Ein normaler Angriff endet nach diesem einen Ziel. Die Zerstörung öffnet die
Linie erst für einen späteren Angriff; Restschaden läuft nicht automatisch zur
nächsten Karte oder zu den Lebenspunkten weiter. Nur eine ausdrückliche
Fähigkeit wie `piercing`, `breakthrough` oder ein später registriertes
Äquivalent darf davon abweichen. Ebenso benötigen Konterzerstörung oder andere
zusätzliche Folgen einen ausdrücklichen Effekt.

## Sichtbare Kampfzahlenskala

Angriffs- und Verteidigungswerte verwenden bewusst die große Anime-/TCG-
Darstellung mit überwiegend drei- bis vierstelligen ganzen Zahlen. Eine
kompakte Skala von etwa 1 bis 15 ist damit nicht die Spielerprojektion des
Battlers.

Der serverseitige Randomizer zieht ATK und DEF aus versionierten, nach Rarity
und Level ansteigenden Korridoren. Die Korridore dürfen sich kontrolliert
überlappen: Eine defensiv ausgerichtete Karte kann einen niedrigeren ATK-Wert
als eine offensiv ausgerichtete Karte der vorherigen Stufe besitzen. Die
höhere Entwicklungsstufe bleibt durch das gesamte Kampf- und Effektbudget
stärker und muss nicht in jedem Einzelwert überlegen sein.

Rollenprofile verteilen das gezogene Kampfbudget beispielsweise offensiv,
defensiv oder ausgeglichen auf ATK und DEF. Zufallsvarianz darf Karten
unterscheidbar machen, aber weder den Raritykorridor sprengen noch eine
Entwicklung verschlechtern. Alle gezogenen Werte, Randomizerrevisionen und
Budgets werden materialisiert und im Match nicht erneut ausgewürfelt.

Als erste verbindliche Balancingpolicy gilt für den jeweils dominanten Wert
einer Karte:

| Entwicklungsstufe | Korridor des dominanten ATK- oder DEF-Werts |
|---|---:|
| Standard | 400–1.000 |
| Common Level 1–3 | 900–1.600 |
| Uncommon Level 1–3 | 1.300–2.000 |
| Rare Level 1–3 | 1.700–2.400 |
| Super Level 1–3 | 2.100–2.800 |
| Ultra Level 1–3 | 2.500–3.300 |
| Legendary | 3.000–4.000 |

Innerhalb einer Rarity liegt Level 1 bevorzugt im unteren, Level 2 im mittleren
und Level 3 im oberen Teil des Korridors. Der Randomizer materialisiert
Grundwerte in Schritten von 50. Karten- und temporäre Effekte dürfen Werte
ausdrücklich jenseits dieser Grundwertkorridore verändern; 4.000 ist daher ein
Legendary-Grundwertcap und kein hartes Laufzeitcap.

Jeder Spieler startet ein Match mit **8.000 Lebenspunkten**. Ein direkter
Angriff durch eine vollständig freie Linie verursacht Schaden in Höhe des
vollständigen aktuellen Angriffswerts des Angreifers. Kampf- und Effektbudget,
Rollenverteilung sowie die genaue Unterteilung der drei Level innerhalb eines
Korridors bleiben versioniert playtestbar, ohne die sichtbare Skala zu ändern.

## Position als Mechanik und Crafting-Eingabe

Keine Karte ist allein aufgrund ihres Bildes fest auf Front oder Back
beschränkt. Randomisiertes Card Crafting darf jedoch positionsbezogene
Mechanikfamilien ziehen, die durch sichtbare Bildbeschreibung thematisch
ausformuliert werden. Ein erster Arbeitsbestand möglicher Rollen ist:

- `vanguard`: Vorteil in einem Frontslot,
- `rear_guard`: Unterstützung aus einem Backslot,
- `ambush`: Wirkung beim Aufdecken,
- `intercept`: Schutz einer benachbarten Linie,
- `sniper`: Zugriff auf hintere Ziele,
- `piercing`: mögliche Wirkung nach Durchbruch,
- `flank`: Vorteil auf einer Außenlinie,
- `center_support`: Wirkung aus `rear_center` auf beide Frontslots,
- `shift`: Positionswechsel nach eigener Regel,
- `expose`: Aufdecken einer gegnerischen verdeckten Karte.

Diese Begriffe sind noch kein abgeschlossener Keywordkatalog. Verbindlich ist
bereits, dass Positionseffekte aus registrierten Regelprimitiven und einem
serverseitigen Budget stammen. Das LLM darf das Bild dazu passend benennen und
beschreiben, aber weder Liniengeometrie noch Targeting- oder Zahlenregeln
erfinden.

Beispielhafte Bildableitungen bleiben Vorschlagsheuristiken und keine
Wahrheitsschreibautorität:

- dynamische Nahaufnahme → möglicher Vanguard- oder Flank-Vorschlag,
- beobachtende Figur im Hintergrund → möglicher Rear-Guard-Vorschlag,
- schattige oder verborgene Darstellung → möglicher Ambush-Vorschlag,
- sichtbare Fernwirkung → möglicher Sniper-Vorschlag,
- unterstützende Geste oder Gruppe → möglicher Center-Support-Vorschlag,
- Tür, Weg oder leerer Korridor → möglicher Linienöffnungs- oder
  Blockadeeffekt.

Der serverseitige Randomizer zieht zuerst zulässige Rolle und Effektbudget;
Bildbeschreibung und LLM liefern erst danach die gebundene thematische
Interpretation.

## Feldpräsenz und Opfer als Ausspielhürde

Stärkere Entwicklungsstufen werden nicht allein durch eine Handressource
ausgespielt. Ihr Einsatz verbindet zwei Voraussetzungen:

1. Bereits gelegte eigene Karten müssen gemeinsam die festgelegte
   Mindestmenge an Feldpräsenz bereitstellen.
2. Danach müssen abhängig von Rarity und Level eine oder mehrere eigene
   Feldkarten geopfert werden.

Jede eigene kontrollierte Feldfigur liefert abhängig von ihrer aktuellen
Rarity folgende Präsenz; ihr Level verändert ihren Beitrag nicht zusätzlich:

| Rarity | Präsenzbeitrag |
|---|---:|
| Standard | 1 |
| Common | 1 |
| Uncommon | 2 |
| Rare | 3 |
| Super | 4 |
| Ultra | 5 |
| Legendary | 6 |

Für das normale Ausspielen gelten anschließend diese Mindestwerte und
Opferkosten:

| Ausgespielte Stufe | Benötigte Präsenz vor dem Opfer | Opfer |
|---|---:|---:|
| Standard | 0 | 0 |
| Common Level 1 | 0 | 0 |
| Common Level 2 | 0 | 0 |
| Common Level 3 | 1 | 0 |
| Uncommon Level 1 | 1 | 0 |
| Uncommon Level 2 | 2 | 0 |
| Uncommon Level 3 | 3 | 0 |
| Rare Level 1 | 3 | 1 |
| Rare Level 2 | 4 | 1 |
| Rare Level 3 | 5 | 1 |
| Super Level 1 | 5 | 1 |
| Super Level 2 | 6 | 1 |
| Super Level 3 | 7 | 2 |
| Ultra Level 1 | 7 | 2 |
| Ultra Level 2 | 8 | 2 |
| Ultra Level 3 | 9 | 2 |
| Legendary | 10 | 3 |

Offene und verdeckte Karten liefern denselben serverseitig bekannten
Präsenzbeitrag. Die Präsenz wird unmittelbar vor dem Opfer geprüft und nicht
ausgegeben. Karten, die zur erfüllten Präsenz beigetragen haben, dürfen
anschließend selbst als Opfer gewählt werden. Jede eigene kontrollierte
Feldfigur ist grundsätzlich ein gültiges Opfer, soweit kein strukturierter
Effekt sie schützt oder ausschließt. Alle Opfer werden atomar bezahlt; eine
unvollständige Zahlung verändert das Feld nicht.

Geopferte Karten schaffen anschließend den benötigten freien Slot. Ein Opfer
ist ein eigener Regelvorgang und nicht automatisch Zerstörung. Effekte dürfen
Präsenz oder Opfer nur über ausdrückliche registrierte Regeln verändern oder
umgehen.

Eine Karte verwendet immer ihre aktuelle höchste Entwicklungsrevision. Es gibt
kein freiwilliges Herunterstufen auf eine frühere, billiger ausspielbare Form.
Super-, Ultra- und Legendary-Karten erhalten dafür ein entsprechend höheres
Fähigkeitsbudget. Die Ausspielhürde erzwingt eine Deckkurve: Leicht spielbare
Standard-, Common- und weitere Aufbaukarten bleiben notwendig; ein Deck nur aus
Legendary-Karten soll nicht funktionsfähig sein.

## Minimaler serialisierbarer Feldzustand

Jede belegte Feldposition benötigt mindestens:

```text
BattlefieldCardState
├─ card_identity_id und card_rules_revision_id
├─ owner_player_id und controller_player_id
├─ slot: front_left | front_right | rear_left | rear_center | rear_right
├─ visibility: face_up | face_down
├─ battle_mode: attack | defense
├─ orientation: ready | exhausted
├─ normal_attacks_used_this_turn
├─ formation_action_used_this_turn
├─ entered_field_turn
├─ base_combat_values und calculated_combat_values
├─ active_effect_instance_ids[]
└─ state_revision
```

Der Matchzustand friert Deck-, Kartenregel-, Board-, Randomizer- und Policy-
Revisionen ein. Renderer und UI projizieren diesen Zustand, berechnen aber
weder Zielreihenfolge, Reveal, Blockade noch Lebenspunkteschaden selbst.

## Testbare Invarianten

1. Jeder Spieler besitzt genau zwei Front- und drei Back-Slots.
2. Jede Spielkarte ist strukturell eine Figurenkarte mit Angriffs- und
   Verteidigungswert und kann grundsätzlich in jedem freien Slot liegen.
3. `front_left` schützt links und Mitte; `front_right` schützt rechts und
   Mitte.
4. Die mittlere Linie kann bei zwei belegten Frontslots nicht direkt auf die
   Lebenspunkte zugreifen.
5. Ein direkter Lebenspunkteangriff ist nur bei einer nach Serverregeln
   vollständig freien gewählten Linie zulässig.
6. Eine verdeckte Karte bleibt gegenüber dem Gegner unbekannt, ist aber in
   Simulation, Save und Replay vollständig gebunden.
7. Ein Angriff auf eine verdeckte Karte deckt sie auf und endet ohne normalen
   Wertevergleich, unmittelbare Kampfzerstörung oder Lebenspunkteschaden.
8. Sichtbarkeit und Kampfmodus sind orthogonal; alle vier Kombinationen sind
   grundsätzlich serialisierbar und regelgültig.
9. Der Browser berechnet weder Guard-Zuordnung noch Targeting, Reveal oder
   Linienfreiheit.
10. Card-Battler-Matches verändern keine Bilddisposition, Championrevision,
    Favorite-Verlustserie oder Delete-or-Live-Projektion.
11. Eine Karte wird ausschließlich in ihrer aktuellen höchsten
    Entwicklungsrevision ausgespielt; frühere Revisionen bleiben Audit- und
    Replayhistorie, aber keine wählbaren Matchformen.
12. Karten mit hoher Ausspielhürde benötigen sowohl vorbestehende
    Feldpräsenz als auch die regelgültige Opferzahlung.
13. Eine Karte im Verteidigungsmodus kann ohne ausdrückliche Fähigkeit keinen
    Angriff deklarieren.
14. Wird eine offene Karte im Verteidigungsmodus mit einem höheren
    Angriffswert angegriffen, wird sie zerstört, ohne dass ihre
    Lebenspunktepartei Differenzschaden erleidet.
15. Wird eine offene Karte im Angriffsmodus mit einem höheren Angriffswert
    angegriffen, wird sie zerstört und die positive Differenz ihren
    Lebenspunkten als Schaden zugefügt.
16. Bei gleichen Angriffswerten werden beide Karten ohne Differenzschaden
    zerstört; bei höherem Zielangriff werden Angreifer und dessen Lebenspunkte
    spiegelbildlich belastet.
17. Gegen gleiche Verteidigung bleiben beide Karten ohne Schaden liegen; gegen
    höhere Verteidigung bleiben beide Karten liegen und nur die Lebenspunkte
    des Angreifers erleiden die Differenz.
18. Ein normaler Angriff trifft genau ein Ziel und erzeugt ohne ausdrückliche
    Fähigkeit weder Restschaden noch eine automatische Fortsetzung entlang der
    Linie.
19. Jede angriffsberechtigte Figur darf ohne ausdrücklichen Effekt genau einen
    normalen Angriff je eigener Angriffsphase erklären.
20. Alle drei hinteren Slots dürfen angreifen, aber ausschließlich entlang
    ihrer jeweils fest zugeordneten Linie.
21. `front_left` darf links oder mittig, `front_right` rechts oder mittig
    angreifen.
22. Eine eigene Frontfigur blockiert keinen Angriff aus dem eigenen hinteren
    Slot.
23. Ein verdeckter Angreifer wird aufgedeckt und setzt seinen Angriff nach den
    Reveal-/Reaktionsfenstern fort, sofern er noch regelgültig angreifen kann.
24. Eine bereits seit Zugbeginn kontrollierte Figur darf einmal in Hauptphase I
    oder II entweder den Kampfmodus wechseln, sich aufdecken oder in einen
    freien eigenen Slot bewegen.
25. Eine im aktuellen Zug neu aufs Feld gekommene oder bereits normal
    angreifende Figur darf keine freiwillige Formationsaktion ausführen.
26. Eine offene Figur darf ohne ausdrücklichen Effekt nicht wieder verdeckt
    werden.
27. Eine Bewegung setzt weder Einsatzverzögerung noch Angriffs- oder
    Nutzungszähler zurück und gilt nicht als Kartenausspielung.
28. ATK und DEF werden als serverseitig materialisierte drei- bis vierstellige
    ganze Zahlen aus versionierten Rarity-/Level-Korridoren dargestellt.
29. Kontrollierte Korridorüberlappung und Rollenvarianz dürfen einzelne Werte,
    aber nicht das Gesamtbudget oder den Fortschritt einer Karte umkehren.
30. Grundwerte werden in 50er-Schritten aus den festgelegten Korridoren
    materialisiert; Legendary besitzt ein Grundwertcap von 4.000, das Effekte
    temporär überschreiten dürfen.
31. Beide Spieler starten mit 8.000 Lebenspunkten; ein direkter Angriff
    verursacht den vollständigen aktuellen ATK-Wert als Schaden.
32. Bei zwei Frontblockern in der mittleren Linie bindet der Angreifer einen
    davon als Ziel; der andere bleibt anschließend ein Blocker der Mitte.
33. Figurenkarten speichern keinen Kampfschaden und besitzen keine eigenen
    Lebenspunkte.
34. ATK und DEF werden nach allen Modifiern mindestens bei null begrenzt.
35. Lebenspunkteschaden, Zerstörung, Opfer, Entfernung und Werteverlust sind
    getrennte Ereignisse und nicht austauschbare Trigger.
36. Standard/Common, Uncommon, Rare, Super, Ultra und Legendary liefern
    grundsätzlich 1, 2, 3, 4, 5 beziehungsweise 6 Präsenz; Standard liefert
    wie Common einen Punkt.
37. Die Ausspielhürde folgt der festgelegten Presence-before-sacrifice-Matrix
    von 0/0 für Standard und niedrige Common bis 10/3 für Legendary.
38. Sichtbarkeit verändert Präsenz nicht; eine zur Präsenz beitragende Karte
    darf anschließend als Opfer dienen.
39. Eine nicht vollständig bezahlbare Opferzahlung verändert das Feld nicht.

## Post-v0.1-Erweiterungen und Playtestkalibrierung

Die Feldbaseline ist abgeschlossen. Spätere Rules-Versionen dürfen Affinitäten,
weitere Deck-Synergieachsen oder zusätzliche Siegbedingungen einführen. Die
Verteilung der Standard-Kampfprofile sowie Kampf- und Effektbudgets werden als
versionierter Content im Playtest kalibriert. Ein Side-/Reserve-Deck gehört
ausdrücklich nicht zu v0.1. Der Umgang mit gelöschten Bildbindungen ist bereits
im Kartenlebenszyklus und in der
[`Runtime-Architektur`](card-battler-runtime-architecture.md) entschieden.
