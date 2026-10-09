# Card Battler – Zonen-, Status- und Opcode-Registry

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für Kartenzonen, Zonenwechsel,
gleichzeitige Pflichttrigger, Target-Selektoren, Statuszustände und die
ausführbaren Regelprimitive der Figurenkarten

Rules-Version: `card_battler_rules_v0.1`

Status: **Baseline abgeschlossen**

Stand: 10. September 2026

## Zweck und Abgrenzung

Dieser Vertrag schließt die simulierbare Grundbibliothek des Card Battlers. Er
definiert keine neuen Kartenarten. Sämtliche Opcodes werden weiterhin nur als
materialisierte Traits universeller Figurenkarten ausgeführt.

Effektbudget, Trigger, Geschwindigkeiten, Ketten und EffectInstance-Cap stehen
in
[`card-battler-effect-grammar-and-llm-authoring.md`](card-battler-effect-grammar-and-llm-authoring.md).
Feldslots, Linien und normaler Kampf stehen in
[`card-battler-board-and-combat-foundation.md`](card-battler-board-and-combat-foundation.md).
Deck- und Zugregeln stehen in
[`card-battler-decks-turns-and-actions.md`](card-battler-decks-turns-and-actions.md).

## Kartenzonen

Jeder Spieler besitzt im Match folgende Zonen:

| Zone | Sichtbarkeit | Ordnung | Zweck |
|---|---|---|---|
| `deck` | verdeckt | serverseitig geordnet | reguläres und effektbasiertes Ziehen |
| `hand` | nur für Besitzer sichtbar | ungeordnet | ausspielbare Karten und Handkosten |
| `field` | abhängig von `face_up`/`face_down` | fünf feste Slots | Figuren, Kampf und Traits |
| `graveyard` | vollständig öffentlich | chronologisch geordnet | zerstörte, geopferte und abgeworfene Karten |
| `banished` | im MVP öffentlich | chronologisch geordnet | für den Rest des Matchs entfernte Karten |

`graveyard` und `banished` sind besitzgebunden. Ein Kontrollwechsel auf dem
Feld verändert niemals den Besitzer. Verlässt eine fremdkontrollierte Karte das
Feld, wechselt sie deshalb in Hand, Deck, Friedhof oder Banished-Zone ihres
Besitzers.

Der Friedhof ist kein zweites Deck. Ohne registrierten Target-Selektor darf
keine Karte daraus gewählt oder bewegt werden. Seine sichtbare Reihenfolge
bleibt für Replay und mögliche `top_of_graveyard`-Effekte erhalten, wird aber
nicht frei sortiert.

### Verbindliche Zonenwechsel

| Ereignis/Opcode | Zielzone | Ereignistyp |
|---|---|---|
| Kampf- oder Effektzerstörung | Friedhof des Besitzers | `destroyed` |
| als Kosten oder regelgültig geopfert | Friedhof des Besitzers | `sacrificed` |
| aus der Hand abgeworfen | Friedhof des Besitzers | `discarded` |
| ohne Zerstörung in den Friedhof gelegt | Friedhof des Besitzers | `sent_to_graveyard` |
| auf die Hand gegeben | Hand des Besitzers | `returned_to_hand` |
| ins Deck zurückgelegt | Deck des Besitzers, danach serverseitig mischen | `returned_to_deck` |
| verbannt | Banished-Zone des Besitzers | `banished` |
| wiederbelebt | gültiger freier Feldslot unter Kontrolle des ausführenden Spielers | `revived` und `entered_field` |

Diese Ereignistypen substituieren einander nicht. `sent_to_graveyard` löst
beispielsweise keinen Destroy-, Sacrifice- oder Discard-Trigger aus.

### Verlassen und erneutes Betreten des Feldes

Beim Verlassen des Feldes endet die bisherige `FieldCardInstance`. Alle an sie
gebundenen EffectInstances, Aura-Projektionen, Modus-, Sichtbarkeits-,
Positions- und flüchtigen Kampfzustände enden. Beim erneuten Betreten entsteht
eine neue FieldCardInstance mit neuem Eintrittszeitpunkt und neuer
Einsatzverzögerung.

Feldlokale Zähler wie `resolved_attack_count` beginnen bei der neuen Instanz
erneut. Bereits verbrauchte once-per-turn- und once-per-match-Nutzungen bleiben
hingegen im `MatchAbilityUsageLedger` an Matchkarte und AbilityRevision
gebunden. Verlassen und Wiederbeleben setzt ein solches Limit nicht zurück.

Wiederbelebung benötigt bei Auflösung einen gültigen freien Slot. Fehlt er,
verpufft der Feldwechsel und die Karte bleibt im Friedhof; bezahlte Kosten
werden nicht erstattet. `banished` ist im initialen MVP eine endgültige
Matchentfernung und besitzt keinen Rückhol-Opcode.

## Gleichzeitige Pflichttrigger

Der Spieler, dessen Zug gerade ausgeführt wird, ist der `active_player`. Wenn
ein atomares Ereignis mehrere Pflichttrigger gleichzeitig erzeugt, besitzt der
aktive Spieler Auflösungspriorität.

Der Server verarbeitet den Triggerblock so:

1. Nach dem Zustandsprüfpunkt werden alle gleichzeitig entstandenen
   Pflichttrigger gesammelt; während der Sammlung wird keiner aufgelöst.
2. Aktiver und nicht aktiver Spieler legen jeweils die gewünschte
   Auflösungsreihenfolge ihrer eigenen Trigger fest. Fehlt eine fristgerechte
   Auswahl, verwendet der Server `ability_revision_id`, danach
   `field_slot_order` als stabilen Fallback.
3. Für die bestehende LIFO-Kette wird zuerst der Block des nicht aktiven
   Spielers in umgekehrter Wunschreihenfolge eingestellt, danach der Block des
   aktiven Spielers ebenfalls umgekehrt.
4. Dadurch löst der aktive Spieler seine gewählte Reihenfolge zuerst auf;
   danach folgt die gewählte Reihenfolge des nicht aktiven Spielers.
5. Erst nachdem alle Pflichttrigger eingestellt wurden, beginnt das normale
   Reaktionsfenster. Der nicht aktive Spieler erhält die erste optionale
   Reaktionsmöglichkeit.
6. Das Sechserlimit der Kette bleibt bestehen. Nicht eingestellte
   Pflichttrigger wechseln in einen deterministischen Folgeblock mit derselben
   Active-player-Priorität.

Diese Regel betrifft die Auflösungsreihenfolge, nicht die Eigentümerschaft eines
Effekts. Wechselt der aktive Spieler während eines besonderen Effekts nicht
ausdrücklich, bleibt der Spieler des laufenden Zugs aktiv.

### Endphasen-Discard

Liegt die Hand des aktiven Spielers bei der Endphasenprüfung über sieben,
wählt er alle erforderlichen Karten gleichzeitig und legt sie in einem
atomaren `hand_limit_discard` in seinen Friedhof. Erst danach werden sämtliche
`on_discard`-, `on_enter_graveyard`- und daraus abgeleiteten Pflichttrigger
gesammelt. Für ihre Reihenfolge gilt dieselbe Active-player-Regel. Nach deren
vollständiger Auflösung wird das Handlimit erneut geprüft, falls Effekte neue
Handkarten erzeugt haben.

## Target-Selector-Registry

Ein Opcode verwendet genau einen registrierten Selektor. Bedingungen wie
offen, verdeckt, Angriffs-/Verteidigungsmodus, Rarity, Linie oder Zone werden
als zusätzliche Filter materialisiert.

| Selector | Bedeutung |
|---|---|
| `self` | ausführende FieldCardInstance |
| `event_source` | Quelle des auslösenden Ereignisses |
| `event_target` | bereits gebundenes Ziel des Ereignisses |
| `attacker` / `defender` | Figur des aktuellen Kampfereignisses |
| `one_ally` / `one_enemy` | eine frei gewählte gültige Feldfigur |
| `adjacent_ally` / `adjacent_enemy` | ein geometrisch benachbartes gültiges Ziel |
| `same_line_ally` / `same_line_enemy` | ein Ziel der gebundenen Angriffslinie |
| `up_to_two` | null bis zwei gültige Ziele der festgelegten Partei und Zone |
| `all_in_line` | alle gültigen Figuren genau einer gebundenen Linie |
| `front_row` / `rear_row` | alle gültigen Figuren der angegebenen Reihe und Partei |
| `own_field` / `enemy_field` / `all_fields` | alle gültigen Figuren des Scopes |
| `owner_player` / `opponent_player` | genau ein Spielerobjekt |
| `one_own_line` / `one_enemy_line` | genau ein Linienobjekt |
| `one_own_graveyard_card` | eine öffentlich gültige Karte im eigenen Friedhof |
| `top_own_graveyard_card` | jüngste gültige Karte im eigenen Friedhof |
| `random_opponent_hand_card` | serverseitig zufällig gezogene gegnerische Handkarte |

Ein Effekt darf keine bestimmte Karte aus der verdeckten gegnerischen Hand
oder einem Deck wählen. Freie Decksuche, Tutoring und gegnerische
Friedhofsmanipulation gehören nicht zum initialen Registry-Schnitt.

## Status-Registry

Status wird entweder als Regelzustand oder als zeitlich begrenzte
EffectInstance geführt. Er ist niemals bloßer Beschreibungstext.

| Status | Auswirkung | Ende/Counterplay |
|---|---|---|
| `summoning_delay` | verhindert normale Angriffe | Beginn des nächsten eigenen Zugs; ausdrücklicher Opcode darf einmalig umgehen |
| `exhausted` | verhindert normalen Angriff, freiwillige Formationsaktion und erneute `exhaust_self`-Zahlung; Verteidigung und Pflichttrigger bleiben aktiv | eigener Start/Refresh |
| `attack_locked` | verhindert normale Angriffserklärung, nicht Verteidigung oder Traits | materialisierte Dauer oder Dispel |
| `movement_locked` | verhindert freiwillige und ausdrücklich als Bewegung markierte Effektbewegung | materialisierte Dauer oder Dispel |
| `mode_locked` | verhindert freiwilligen und effektbasierten Moduswechsel | materialisierte Dauer oder Dispel |
| `silenced` | verhindert Aktivierung und neue Trigger eigener Traits; passive Source-bound-Projektionen enden | materialisierte Dauer oder Dispel |
| `destroy_ward` | verhindert genau die nächste passende Zerstörung und wird verbraucht | Verbrauch, Dauerende oder Dispel |
| `target_ward` | verhindert neue gegnerische Zielbindung des registrierten Scopes | Dauerende, Dispel oder nicht zielende Wirkung |
| `direct_attack_ward` | verhindert oder negiert genau den nächsten direkten Angriff gemäß Blueprint | Verbrauch oder Dauerende |

`silenced` entfernt keine bereits unabhängige Fixed-duration-EffectInstance,
deren Quelle nicht mehr fortlaufend benötigt wird. Sie beendet jedoch Auren und
andere `while_source_active`-Projektionen der verstummten Figur. Silence ändert
weder ATK/DEF-Grundwert noch Sichtbarkeit oder Kampfmodus.

Ward verhindert niemals eine freiwillig bezahlte Opferkostenhandlung ihres
Controllers. Ein bereits bezahltes Opfer kann nicht nachträglich verhindert,
negiert oder zurückerstattet werden.

## Opcode-Registry v0.1

### Werte und Information

| Opcode | Wirkung | Mindest-Rarity |
|---|---|---|
| `modify_atk_add` / `modify_def_add` | additiver Buff oder Debuff im gültigen Zahlenkorridor | Common |
| `reveal_card` | deckt eine Feldkarte auf und erzeugt den passenden Reveal-Grund | Common |
| `change_battle_mode` | setzt Angriff oder Verteidigung | Common |
| `set_face_down` | verdeckt eine offene Figur durch Effekt; startet Arming neu | Rare |
| `inspect_top_deck` | zeigt dem Besitzer die obersten `N` Karten ohne Umordnung | Uncommon |
| `reorder_top_deck` | ordnet eine kleine, materialisierte Zahl eigener oberster Karten | Rare |

Prozentuale, verdoppelnde, halbierende und `set_stat_value`-Effekte sind im
initialen MVP nicht registriert. ATK und DEF bleiben additiv.

### Position und Linien

| Opcode | Wirkung | Mindest-Rarity |
|---|---|---|
| `move_to_free_slot` | bewegt eine Figur in einen gültigen freien Slot ihres Controllers | Common |
| `swap_allied_slots` | tauscht zwei eigene Feldfiguren atomar | Uncommon |
| `lock_movement` / `lock_mode` | erzeugt den passenden Status | Uncommon |
| `lock_line_attacks` | verhindert weitere normale Angriffe der gebundenen Linie | Rare |
| `lock_slot` | verhindert zeitweise das Belegen eines leeren Slots | Super |

Eine Bewegung verändert Besitz, Einsatzverzögerung, Angriffsverbrauch und
Ability-Ledger nicht. Ist ein Zielslot bei Auflösung belegt, verpufft die
Bewegung, soweit der Blueprint keinen atomaren Swap verwendet.

### Kampf

| Opcode | Wirkung | Mindest-Rarity |
|---|---|---|
| `negate_current_attack` | beendet die aktuelle Attacke ohne Kampfvergleich | Common, nur selbst-/angreiferbezogene Reaktion |
| `restrict_next_attack` | erzeugt `attack_locked` für den registrierten Umfang | Common |
| `redirect_attack_to_self` | macht eine gültige eigene Figur einmalig zum neuen Ziel | Uncommon |
| `grant_immediate_attack` | umgeht Einsatzverzögerung für genau einen registrierten Angriff | Rare |
| `grant_extra_attack` | erlaubt einen zusätzlichen normalen Angriff | Rare |
| `piercing_damage` | bei Zerstörung eines offenen Verteidigungsziels geht die positive Differenz an dessen Spieler | Rare |
| `target_rear_in_line` | darf beim Zielschritt den Back-Slot derselben Linie trotz Frontblocker binden | Rare |
| `breakthrough_damage` | bei Zerstörung eines offenen Angriffsziels geht ein budgetierter Anteil der positiven Differenz zusätzlich an den Spieler | Super |
| `prevent_direct_attack` | erzeugt `direct_attack_ward` | Uncommon |

Eine Figur darf auch mit Effekten höchstens zwei normale Angriffe in derselben
eigenen Angriffsphase vollständig ausführen. Eine Attacke darf höchstens einmal
umgeleitet werden. `target_rear_in_line` öffnet niemals einen direkten Angriff,
solange irgendein regelgültiger Linienverteidiger existiert.

### Feldwechsel und Friedhof

| Opcode | Wirkung | Mindest-Rarity |
|---|---|---|
| `destroy_figure` | zerstört eine Figur und sendet sie in den Friedhof | Uncommon |
| `send_to_graveyard` | bewegt ohne Destroy-Ereignis in den Friedhof | Rare |
| `return_to_owner_hand` | gibt eine Feldfigur auf die Besitzerhand | Uncommon |
| `return_to_owner_deck` | legt ins Besitzerdeck zurück und mischt | Rare |
| `recover_graveyard_to_hand` | nimmt eine gültige eigene Friedhofskarte auf die Hand | Uncommon |
| `revive_from_graveyard` | bringt eine eigene Friedhofskarte mit Einsatzverzögerung in einen freien Slot | Rare |
| `banish_figure` | entfernt eine Feldfigur für den Rest des Matchs | Ultra |

`sacrifice_self` und `sacrifice_ally` sind Aktivierungskosten, keine
Destroy-Opcodes. Der MVP besitzt keinen Opcode, der den Gegner zwingt, eine
Figur als Opfer anzubieten.

### Schutz, Dispel und Negate

| Opcode | Wirkung | Mindest-Rarity |
|---|---|---|
| `grant_destroy_ward` | verhindert einmalig Kampf- oder Effektzerstörung im materialisierten Scope | Uncommon |
| `grant_target_ward` | verhindert neue gegnerische Zielbindung, nicht Flächenwirkung | Rare |
| `dispel_effect_instance` | entfernt genau eine gültige fortdauernde EffectInstance | Rare |
| `silence_traits` | erzeugt `silenced` auf einer Figur | Super |
| `negate_activation` | negiert das aktuelle aktivierte oder getriggerte Kettenglied | Super, Geschwindigkeit 3 |
| `negate_opcode` | negiert genau einen registrierten Opcode eines mehrteiligen Kettenglieds | Super, Geschwindigkeit 3 |

Negate erstattet keine Kosten und kann keinen passiven Speed-0-Zustand als
Aktivierung treffen. Passive Quellen werden durch Silence, Dispel ihrer
Projektion, ungültige Position oder Entfernen der Quelle bekämpft. Ein
Destroy-Ward schützt nicht vor Opfer, Return, Banish oder Send-to-graveyard.
Eine Target-Ward schützt nicht vor nicht zielenden Flächenwirkungen.

Blanket-Immunität gegen „alle Effekte“ ist im MVP nicht registriert. Jeder
Schutz nennt Opcodefamilie, Quelle, Dauer und Verbrauch ausdrücklich.

### Hand, Spieler und Aktionsökonomie

| Opcode | Wirkung | Mindest-Rarity |
|---|---|---|
| `draw_cards` | zieht die materialisierte Zahl vom eigenen Deck | Common mit Ereignis/Kosten, sonst Uncommon |
| `discard_own` | legt gewählte eigene Handkarten ab | Common als Kosten, Uncommon als Wirkung |
| `discard_random_opponent` | lässt den Server eine zufällige gegnerische Handkarte abwerfen | Rare |
| `deal_lp_damage` / `heal_lp` | verändert LP innerhalb des Raritycaps | Common |
| `grant_play_action` | erhöht genau eines der beiden Hauptphasenlimits um eins; kein Übertrag | Rare |
| `reduce_play_action` | senkt ein kommendes Hauptphasenlimit höchstens um eins | Super |

Pflichtziehen aus leerem Deck bleibt eine Niederlage. Effektziehen, das nicht
vollständig erfüllt werden kann, verwendet denselben Pflichtziehvertrag, sofern
der Blueprint es nicht ausdrücklich als `draw_up_to` materialisiert. Heilung
kann 8.000 LP im MVP nicht überschreiten. Direktschaden darf nie als
unkonterbare Kostenwirkung auf den Gegner geschrieben werden.

## Ausdrücklich nicht im initialen MVP

Die folgenden Mechaniken sind nicht Teil der ausführbaren Registry:

- Kartenduplikation, Kopien oder Tokens,
- freie Decksuche und Tutoring,
- gegnerische Friedhofsmanipulation,
- Rückholung aus `banished`,
- dauerhafte oder zugübergreifende Kontrollübernahme,
- Prozentwerte, Verdopplung, Halbierung und Set-to-value,
- nicht spezifizierte Blanket-Immunität,
- unendliche Wiederholung oder ein Loop ohne sinkendes Ausführungsbudget,
- sowie Effekte, die neue Kartentexte oder Opcodes während des Matchs erzeugen.

Neue Primitive benötigen eine neue Rules-Version, feste Kosten, Rarity-Gate,
Target-Regel, Gegenwehr und Replay-Fixtures. Die LLM kann sie nicht durch eine
kreative Beschreibung einführen.

## Testbare Invarianten

1. Destroy, Sacrifice und Discard bewegen die Besitzerkarte in den öffentlichen
   Friedhof, erzeugen aber unterschiedliche Ereignistypen.
2. Control verändert Ownership und Zielzone beim Feldverlassen nicht.
3. Zone Change beendet die alte FieldCardInstance und alle daran gebundenen
   EffectInstances.
4. Wiederbetreten erzeugt Einsatzverzögerung und neue Feldzähler, setzt jedoch
   once-per-turn/once-per-match-Nutzungen nicht zurück.
5. Banish ist im MVP eine öffentliche, endgültige Matchentfernung.
6. Bei gleichzeitigen Pflichttriggern löst der aktive Spieler seine gewählte
   Reihenfolge vor dem nicht aktiven Spieler auf.
7. Der nicht aktive Spieler erhält nach Einstellung aller Pflichttrigger die
   erste optionale Reaktion.
8. Handlimit-Discard erfolgt atomar; Trigger entstehen erst nach dem gesamten
   Discard und vor einer erneuten Handlimitprüfung.
9. Jeder Target Selector stammt aus der Registry und bindet keine bestimmte
   verdeckte gegnerische Hand- oder Deckkarte.
10. Silence, Dispel und Negate bleiben getrennte Opcodes mit unterschiedlicher
    Wirkung.
11. Destroy-Ward verhindert weder Opfer noch Return, Banish oder
    Send-to-graveyard.
12. Eine Figur führt je eigener Angriffsphase auch mit Effekten höchstens zwei
    normale Angriffe aus; jeder Angriff wird höchstens einmal umgeleitet.
13. Der initiale Zahlenlayer ist ausschließlich additiv.
14. Kein ausführbarer Effekt erzeugt Kopien, Tokens, Blanket-Immunität oder
    neue Regeln aus Natursprachentext.

## Post-v0.1-Playtestkalibrierungen

- genaue Gewichte der einzelnen Opcodes innerhalb ihrer TraitLineages,
- maximale Dauer von Silence, Target-Ward, Slot Lock und Spielaktionssenkung,
- UI-Symbole und Vorschau für Friedhof, Banish, Status, Triggerblock und Dispel,
- sowie Häufigkeit von Wiederbelebung, Banish und Speed-3-Countern im 40er-Deck.

Die Kalibrierungen ändern keine Zonen-, Triggerprioritäts-, Target- oder
Opcode-Autorität der abgeschlossenen v0.1-Registry. Neue Primitive benötigen
eine neue Rules-Version.
