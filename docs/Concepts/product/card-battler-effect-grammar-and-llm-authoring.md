# Card Battler – Effektgrammatik und LLM-Authoring

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für Effektformen, bildbezogene
LLM-Kontextualisierung, Entwicklungsbudget und ausführbare Regelgrenzen der
universellen Figurenkarten

Rules-Version: `card_battler_rules_v0.1`

Status: **Baseline abgeschlossen**

Stand: 10. September 2026

## Zweck und Inspirationsrahmen

Der Card Battler übernimmt die große funktionale Breite klassischer Trading
Card Games wie Magic: The Gathering, Yu-Gi-Oh! und Pokémon, aber nicht deren
getrennte Kartenarten. Jede reguläre Spielkarte bleibt eine Figurenkarte mit
Angriffs- und Verteidigungswert. Was in anderen Spielen als Zauber, Falle,
Trainer, Item, Aura oder Support auf einer eigenen Karte stehen könnte, wird
hier als bildbezogenes Fähigkeitsmodul derselben Figurenkarte materialisiert.

Dieses Dokument definiert,

- welche strukturellen Formen solche Effekte besitzen,
- wie einmalige, gebundene, spielergerichtete, fallenartige und dauerhafte
  Wirkungen unterschieden werden,
- welche Teile kontrolliert zufällig gezogen werden,
- wie ein lokales LLM einen feststehenden Effekt bildbezogen erklärt,
- wie Rarity und Level das Effektbudget steigern,
- und weshalb ausschließlich validierte strukturierte Regeln ausführbar sind.

Spielfeld, Linien, Sichtbarkeit und Kampfmodus stehen in
[`card-battler-board-and-combat-foundation.md`](card-battler-board-and-combat-foundation.md).
Branding, Rarity und Kartenlebenszyklus stehen in
[`card-crafting-and-playground-combination-lifecycle.md`](card-crafting-and-playground-combination-lifecycle.md).
Friedhof, Active-player-Pflichttrigger, Statuszustände, Targets und die
vollständige initiale Opcode-Registry stehen in
[`card-battler-zones-statuses-and-opcode-registry.md`](card-battler-zones-statuses-and-opcode-registry.md).

## Eine Kartenart, viele Effektformen

`Falle`, `Zauber`, `Support` und `Verteidigung` sind keine strukturellen
Kartentypen. Sie beschreiben die Form, in der eine Figurenfähigkeit ausgelöst,
gebunden und aufgelöst wird. Eine Karte darf abhängig von ihrem aktuellen
Entwicklungsbudget eine Primärfähigkeit und später verwandte Erweiterungen
besitzen.

## Trait-System und harmonische Entwicklung

Eine bildlose Standard-CardIdentity ist zunächst eine reine Figurenkarte mit
ATK, DEF und einem daraus abgeleiteten offensiven, defensiven oder
ausgeglichenen Kampfprofil. Sie besitzt noch keinen Trait und keinen
ausführbaren Karteneffekt. Das Branding bewahrt Identität und Kampfprofil,
macht aber nicht das Bild selbst zur Mechanikquelle.

Jeder gültige Entwicklungsschritt erhöht das Kartenbudget und materialisiert
genau eine primäre Trait-Aktion:

```text
kein Trait vorhanden
→ ersten Trait hinzufügen

Trait vorhanden und ausbaubar
→ vorhandenen Trait in Zahl, Dauer, Ziel, Timing, Nutzung oder Rider steigern

weiterer Trait-Slot frei
→ neuen, zum bisherigen Stamm kompatiblen Trait hinzufügen
```

Der Übergang von Standard zu Common Level 1 ist damit der erste Level Up und
erzeugt zwingend den ersten Trait. Ein Keep beginnt mindestens an diesem Punkt.
Ein Favorite auf Rare Level 1 durchläuft serverseitig die übersprungenen
Common-/Uncommon-Schritte als persistierte virtuelle Entwicklungshistorie,
statt isoliert eine fertige Rare-Fähigkeit auszuwürfeln.

Ein Entwicklungsschritt darf aus visueller Bewährung oder einer bestätigten
CardBattleExperience-Schwelle stammen. Die Herkunft autorisiert nur das Level
Up; sie ändert weder Budgetformel noch Trait-Grammatik. Der Card-Battler-Reducer
berechnet keine Promotion, und die LLM entscheidet weder Erfahrungsschwelle
noch Rarity. Jede post-originäre Promotion erhält zusätzlich eine getrennte
visuelle CardEvolutionRevision nach dem Crafting-Vertrag.

Beim ersten Trait bindet der Randomizer eine `TraitLineage` mit einem
mechanischen Ankerprofil und einer versionierten Kompatibilitätsmatrix. Ein
neuer Trait ist nur gültig, wenn er den bestehenden Stamm unterstützt, etwa
durch gemeinsamen Trigger, Zieltyp, Positionsbezug, Kostenbezug oder Payoff.
Widersprüchliche Anforderungen, Selbstblockade, bedeutungslose Kombinationen
und unkonterbare Schleifen sind ungültig. Dadurch kann eine Karte beispielsweise
Reveal → Schutz → Intercept entwickeln, aber nicht ohne verbindendes Element
zwischen zufälligen Reveal-, Draw- und Direktschadenseffekten springen.

Die maximale Zahl gleichzeitig eigener Traits lautet:

| Entwicklungsstufe | Trait-Cap |
|---|---:|
| Standard | 0 |
| Common | 1 |
| Uncommon | 2 |
| Rare | 2 |
| Super | 3 |
| Ultra | 3 |
| Legendary | 3 |

Ist das Cap erreicht, muss ein Level Up einen vorhandenen Trait steigern. Der
Legendary-Schritt entwickelt genau einen vorhandenen Ankertrait zu einem
klaren Capstone, statt einen vierten unabhängigen Trait anzuhängen. Ein Rider
ist eine begrenzte Erweiterung desselben Traits und kein verdeckter zusätzlicher
Trait. Favorite- und ChampionAugments verwenden dieselbe Entwicklungslogik und
umgehen weder Trait-Cap noch Harmonieprüfung.

Die Auswahl zwischen zulässigem Trait-Upgrade und Trait-Zugang erfolgt
reproduzierbar durch den serverseitigen Randomizer aus Rarity, Level,
TraitLineage, Collection-Coverage und Craft Seed. Die semantische
Bildbeschreibung wird dabei nicht ausgewertet. Erst danach formuliert die LLM
Name, Trait-Bezeichnung und Erklärung passend zur sichtbaren Figur und
Situation, ohne die Mechanik zu verändern.

### Einmaliger Effekt

Ein einmaliger Effekt wird in genau einem gültigen Fenster ausgelöst,
vollständig abgearbeitet und danach beendet. Typische Auslöser sind:

- beim offenen Ausspielen,
- beim eigenen Aufdecken,
- beim Aufdecken durch einen gegnerischen Angriff,
- beim Deklarieren eines Angriffs,
- nach gewonnenem oder verlorenem Kampf,
- beim Opfern oder Zerstörtwerden,
- sowie zu Beginn oder Ende eines Zuges.

Der Effekt darf einen Zustand verändern oder eine weitere Wirkung erzeugen;
die Figurenkarte selbst bleibt grundsätzlich in ihrem Slot, sofern kein
ausdrücklicher Opcode sie bewegt, opfert, zerstört oder auf die Hand gibt.

### Effekt auf eine andere Figur

Eine Fähigkeit darf eine andere eigene oder gegnerische Figurenkarte als Ziel
wählen und dort eine revisionierte `EffectInstance` erzeugen. Diese kann
beispielsweise Angriff oder Verteidigung verändern, einen Kampfmodus erzwingen,
Schutz verleihen, eine Fähigkeit sperren, ein Reveal auslösen oder Bewegung
erlauben.

Die Zielkarte speichert die Bindung; ob die UI sie als Marker, Verbindung,
Overlay oder andere visuelle Anheftung zeigt, bleibt eine Präsentationsfrage.
Die Quellkarte verlässt ihren Slot nicht allein deshalb, weil ihr Effekt auf
einer anderen Figur liegt.

### Effekt gegen oder für einen Spieler

Eine Fähigkeit darf den gegnerischen oder eigenen Spieler adressieren,
beispielsweise durch:

- begrenzten direkten Lebenspunkteschaden oder Heilung,
- Kartenziehen oder kontrolliertes Ablegen,
- Änderung eines registrierten Zieh-, Ausspiel- oder Nutzungslimits,
- Einschränkung oder Erleichterung der nächsten Ausspielhandlung,
- sowie Schutz vor dem nächsten direkten Linienangriff.

Spielereffekte benötigen besonders enge rarityabhängige Zahlenbudgets. Sie
dürfen Linienfreiheit, Aufdeckangriff und Opferkosten nicht durch freien
Natursprachentext umgehen.

### Falleneffekt

Ein Falleneffekt wartet auf ein gegnerisches oder kampfbezogenes Ereignis und
reagiert in einem zulässigen Fenster. Er ist häufig, aber nicht zwingend, an
`face_down` und Reveal gebunden. Typische Fenster sind:

- diese Karte wird angegriffen oder aufgedeckt,
- eine benachbarte Karte wird Ziel,
- der Gegner spielt oder opfert eine Karte,
- der Gegner wechselt einen Kampfmodus,
- oder ein direkter Lebenspunkteangriff wird deklariert.

Der erste normale Angriff auf eine verdeckte Karte bleibt ein reiner
Aufdeckangriff. Ein dabei ausgelöster Falleneffekt wird zusätzlich aufgelöst,
führt aber nicht still zu dem sonst ausgeschlossenen normalen Wertevergleich.

### Dauer-, Support- und Auraeffekt

Ein dauerhafter Effekt gilt, solange seine registrierte Bedingung erfüllt ist,
beispielsweise solange die Quelle offen liegt, im Verteidigungsmodus bleibt,
einen bestimmten Slot besetzt oder nicht erschöpft ist. Er kann sich richten
auf:

- dieselbe Karte,
- eine benachbarte Figur,
- die eigene linke, mittlere oder rechte Linie,
- Front- oder Back-Slots,
- alle eigenen Figuren,
- oder einen eng begrenzten globalen Zustand.

Verdeckte Karten erzeugen standardmäßig keine öffentliche Aura. Ein Effekt,
der bereits verdeckt wirkt, muss dies ausdrücklich als verborgenes
Regelprimitiv deklarieren und benötigt eine klar definierte Offenlegung.

### Aktivierter zauberartiger Effekt

Eine offene Figurenkarte darf eine aktivierbare Fähigkeit besitzen. Deren
Kosten können unter anderem Erschöpfen, Moduswechsel, Ablegen einer Handkarte,
Opfern oder ein Nutzungslimit sein. Der Effekt macht die Karte nicht zu einer
Zauberkarte und entfernt sie nicht automatisch vom Feld.

Eine häufige Basiskostenform ist `exhaust_self`: Die Karte kann ihre
zauberartige Fähigkeit nutzen, aber in demselben Bereitschaftszyklus nicht
zusätzlich normal angreifen. Die genaue Refresh- und Aktionsökonomie wird mit
dem Zugphasenvertrag festgelegt.

## Verbindliche Triggerfenster

Ein Trait erhält keinen freien Prosasatz wie „wenn etwas Passendes passiert",
sondern genau registrierte Ereignisse und Bedingungen. Der Server bewahrt für
jedes Ereignis den Zustand unmittelbar vor seiner Auslösung. Dadurch bleibt
beispielsweise prüfbar, ob eine Karte beim Angriff noch verdeckt war, selbst
wenn sie als Teil desselben Ereignisses aufgedeckt wird.

| Trigger-ID | Öffnet sich | Verbindliche Abgrenzung |
|---|---|---|
| `on_play_face_up` | nach einem gültigen offenen Ausspielen | Ein offenes Ausspielen ist kein Flip und erfüllt keinen Reveal-Trigger. |
| `on_reveal` | nach einem regelgültigen Aufdecken | Der Blueprint filtert optional `manual`, `attacked` oder `effect`; bloße UI-Animation zählt nicht. |
| `on_armed_reveal` | beim Reveal nach erfüllter Verdecktdauer | Benötigt `face_down_rounds_completed >= n`; offenes Ausspielen kann den Trigger nie auslösen. |
| `on_attacked_while_face_down` | nach gültiger Zielbindung, vor dem Reveal | Prüft den Zustand vor dem Aufdecken; der normale Angriff bleibt auch nach der Trait-Auflösung ein Reveal-only-Angriff. |
| `on_attacked_while_face_up` | nach gültiger Zielbindung, vor dem Wertevergleich | Erlaubt Schutz, Konter, Umleitung oder Werteänderung im Reaktionsfenster. |
| `on_attack_declared` | nach einer gültigen eigenen Angriffserklärung | Eine später negierte oder abgebrochene Attacke hat diesen Trigger bereits erzeugt. |
| `on_attack_resolved` | nach vollständigem Abschluss des eigenen Angriffs | Ein Reveal-only-Angriff zählt als aufgelöst; eine negierte oder vor Auflösung abgebrochene Attacke nicht. |
| `on_resolved_attack_count` | beim erstmaligen Erreichen von `n` aufgelösten Angriffen | Der Zähler gehört zur Karteninstanz im laufenden Match; Wiederholung muss ausdrücklich registriert sein. |
| `on_combat_result` | nach `won`, `lost` oder `survived` | Zerstörung und Lebenspunkteschaden werden weiterhin als getrennte Ereignisse behandelt. |
| `on_destroyed` / `on_sacrificed` | nach dem jeweiligen getrennten Ereignis | Kein Ereignis substituiert das andere. |
| `on_turn_start` / `on_turn_end` | an der registrierten Zuggrenze | Controller oder Gegner sowie eigene oder gegnerische Zuggrenze sind Teil des Blueprints. |
| `activated_main_phase` | durch bewusste Aktivierung einer offenen Figur | Verbraucht die registrierten Kosten und verwendet Geschwindigkeit 1, soweit kein Blueprint ausdrücklich anderes festlegt. |

### Eine Runde verdeckt und Fallenbereitschaft

`face_down_rounds_completed = 1` bedeutet: Die Karte lag bereits bei einer
eigenen Endphase verdeckt, blieb während des vollständigen folgenden
gegnerischen Zuges ununterbrochen verdeckt und erreicht danach die nächste
eigene Startphase. Dort wird sie `armed`. Eine erst im gegnerischen Zug
verdeckte Karte überspringt diese Strecke nicht, sondern muss zunächst die
nächste eigene Endphase verdeckt erreichen. Das offene Ausspielen löst diese
Fallenbereitschaft nicht ersatzweise aus. Wird die Karte vorher aufgedeckt,
entfernt, zerstört oder auf die Hand gegeben, verfällt der Fortschritt. Ein nur
durch registrierten Effekt erlaubtes erneutes Verdecken beginnt die Zählung von
vorn.

Ein Blueprint darf als schwächere Variante `arming_delay = 0` verwenden. Das
ist ausdrücklich eine eigene Budgetentscheidung: Die Fähigkeit kann dann
bereits beim ersten gegnerischen Angriff auf die frisch verdeckte Karte
reagieren. Ohne solche Angabe gilt für `on_armed_reveal` und bewaffnete
Falleneffekte die volle Runde Wartezeit.

## Starter-Registry für zauber- und fallenartige Traits

Die folgenden Familien bilden den ersten verbindlichen Mechanikraum. Es sind
keine zusätzlichen Kartentypen und keine Kopien konkreter Fremdkarten. Der
Randomizer zieht einen Blueprint aus dieser Registry, materialisiert alle
Parameter und lässt ihn erst danach bildbezogen benennen.

| Mechanische Familie | Typische Trigger/Form | Kernwirkung | Natürliche Upgradeachsen | Notwendige Gegenwehr |
|---|---|---|---|---|
| `formation_amplifier` | offene Aura oder gebundener Support | ATK und/oder DEF wachsen mit der Zahl oder Position eigener offener Figuren | Zahlenwert, Cap, Nachbarschaft, zweite Wertachse, geteilter Bonus | Quelle aufdecken/entfernen, Formation auseinanderziehen, festes Cap |
| `revealing_stasis` | offenes Ausspielen, Reveal oder bewaffneter Reveal | deckt Ziele auf und sperrt begrenzt Angriffe, Linien oder direkte Angriffe | Einzelziel → Linie → Formation, Dauer, Auswahl, Reveal-Rider | kurze Dauer, klarer Scope, Negate oder Quellenentfernung |
| `symmetric_collapse` | aktivierter Zaubereffekt oder seltener bewaffneter Reveal | zerstört Karten auf beiden Seiten nach gleicher Scope-Regel | einzelne Linie → Reihe → Feld, Ausnahmen, Nachwirkung | hohe Kosten, Geschwindigkeit 1, symmetrisches Risiko, Nutzungslimit |
| `veiled_ambush` | Angriff auf diese verdeckte Karte | Reveal mit Debuff, Positionswechsel, Angriffsabbruch oder bedingtem Konter | Arming, Höhe, Zielreichweite, zusätzlicher Rider | frühes Reveal, Negate, anderer Angriffsweg, Schwellenbedingung |
| `open_guard` | Angriff auf diese offene Karte | DEF-Schub, einmaliger Zerstörungsschutz, Umleitung oder Rückstoß | Zahlenwert, verbundene Figur, Linie, Nutzungen | Entfernung vor Kampf, Trait-Sperre, verbrauchbarer Schutz |
| `battle_momentum` | aufgelöster Angriff oder erreichter Angriffszähler | wachsender Buff, Refresh, Bewegung oder einmalige Zusatzattacke | Schwelle, Cap, Belohnung, Resetzeitpunkt | Angriff verhindern, Quelle entfernen, Zähler matchlokal begrenzen |
| `bound_support` | offenes Ausspielen, Reveal oder Hauptphasenaktivierung | legt eine revisionierte `EffectInstance` auf eine andere Figur | Zielauswahl, Dauer, Wert, Zusatzschutz, Umlenkung | Quelle oder Ziel entfernen, Dispel, Instanzlimit |
| `counterseal` | Reaktion auf Trait-Aktivierung oder Trigger | negiert Aktivierung, Opcode oder Zielbindung in engem Scope | zulässige Familien, Kosten, Nutzungen, Geschwindigkeit | höhere Countergeschwindigkeit, Kosten erzwingen, einmal pro Zug/Match |
| `sacrifice_exchange` | eigenes Opfern, Geopfertwerden oder Zerstörtwerden | tauscht Feldwert gegen Ziehen, Rückholung, Buff oder gegnerischen Verlust | Ereignisfilter, Wert, Ziel, verzögerte Auszahlung | Sacrifice/Destroy nicht gleichsetzen, Friedhof sperren, Nutzungslimit |
| `line_control` | Hauptphasenaktivierung, Reveal oder Kampfreaktion | bewegt Figuren, wechselt Modi oder sperrt einen Slot/eine Linie zeitweise | Reichweite, Zwang, Dauer, verbundener Buff | freie Zielprüfung, Positionsschutz, kurze Dauer, Quellenentfernung |

### Erster konkreter Blueprint-Pool

Die folgenden Arbeitsnamen dienen nur der Designkommunikation. Die Mechanik-ID
und ihre materialisierten Parameter sind autoritativ; später darf die LLM einen
zum Bild passenden Namen und Erklärungstext liefern. `X`, `N` und `C` sind
serverseitig gezogene, raritygebundene Werte, keine LLM-Platzhalter.

| Arbeitsname / Blueprint | Vollständig definierte Grundauflösung |
|---|---|
| **Geschlossene Formation** / `formation_amplifier.self` | Solange diese Figur offen liegt, erhält sie `+X ATK` je anderer eigener offener Figur, höchstens `+C`. Upgrades dürfen DEF oder eine benachbarte Figur einbeziehen. |
| **Geteilte Stärke** / `formation_amplifier.bound` | Beim offenen Ausspielen oder Reveal wird eine eigene offene Figur gewählt. Solange die Quelle offen bleibt, erhält das Ziel einen begrenzten Bonus für jede weitere eigene offene Figur. Quellen- oder Zielverlust beendet die Instanz. |
| **Enthüllende Ruhe** / `revealing_stasis.single` | Beim offenen Ausspielen oder Reveal wird eine gegnerische verdeckte Figur aufgedeckt; sie darf bis zum Ende ihres nächsten eigenen Zuges keinen normalen Angriff erklären. |
| **Stillgelegte Linie** / `revealing_stasis.line` | Bei einem bewaffneten Reveal werden alle gegnerischen Figuren derselben Linie aufgedeckt; in der laufenden Angriffsphase können aus dieser Linie keine weiteren normalen Angriffe erklärt werden. |
| **Gegenseitiger Fall** / `symmetric_collapse.lane` | In der eigenen Hauptphase wird die Quelle geopfert; danach werden alle übrigen Figuren einer gewählten Linie auf beiden Seiten zerstört. Ungültige oder inzwischen leere Linien folgen der Fizzle-Regel, die Opferkosten bleiben bezahlt. |
| **Leeres Feld** / `symmetric_collapse.field` | Ultra-/Legendary-Capstone, Geschwindigkeit 1, once per match: Nach erheblicher registrierter Zahlung werden alle Figuren beider Seiten einschließlich der Quelle zerstört. Bis zum Zugende sind keine direkten Angriffe des Aktivierenden erlaubt. |
| **Geduldiger Hinterhalt** / `veiled_ambush.armed` | Wird diese bewaffnete verdeckte Figur angegriffen, wird sie aufgedeckt, der Angriff negiert und der Angreifer in Verteidigung versetzt. Frühes Reveal oder Negate verhindert die Wirkung. |
| **Verdeckter Widerstand** / `veiled_ambush.immediate` | Wird diese verdeckte Figur angegriffen, wird sie aufgedeckt und der Angreifer verliert bis zum Ende des Kampfereignisses `X ATK`; der Angriff bleibt Reveal-only. Diese schwächere Form darf `arming_delay = 0` besitzen. |
| **Standhafte Antwort** / `open_guard.self` | Wird diese offene Verteidigungsfigur angegriffen, erhält sie einmal pro Zug bis zum Ende des Kampfereignisses `+X DEF`. Der normale Verteidigungsrückstoß verwendet anschließend den veränderten Wert. |
| **Dritter Anlauf** / `battle_momentum.threshold` | Nachdem diese Karteninstanz ihren `N`-ten normalen Angriff im Match vollständig aufgelöst hat, erhält sie eine einmalige budgetierte Belohnung: dauerhaften Match-Buff, Refresh oder einen für den nächsten Zug vorgemerkten Zusatzangriff. Die konkrete Variante wird beim Crafting festgeschrieben. |
| **Schutzbund** / `bound_support.ward` | Beim offenen Ausspielen oder Reveal wird eine benachbarte eigene Figur gewählt. Das nächste Mal, wenn sie zerstört würde, wird die Zerstörung verhindert und die gebundene EffectInstance verbraucht. |
| **Enges Siegel** / `counterseal.targeted` | Wenn ein gegnerischer Trait eine Figur in derselben Linie als Ziel bindet, darf die offene Quelle ihre registrierten Kosten zahlen, um genau diesen zielgerichteten Opcode zu negieren. Nicht zielende Feldwirkungen bleiben unberührt. |
| **Preis des Einsatzes** / `sacrifice_exchange.draw` | Wird diese Figur geopfert, zieht ihr Controller eine Karte oder erhält einen raritybegrenzt ausgewählten Rückhol-Effekt. Zerstörtwerden löst den Trait ausdrücklich nicht aus. |
| **Positionsbruch** / `line_control.displace` | Beim Reveal wird eine Figur derselben Linie in einen gültigen freien Slot ihres Controllers bewegt und optional ihr Modus gewechselt. Existiert bei Auflösung kein gültiger Slot, verpufft die Bewegung. |

Der Pool trennt absichtlich verwandte, aber nicht identische Wirkungen. Eine
Karte mit `Geduldiger Hinterhalt` hat beispielsweise nicht automatisch auch
`Standhafte Antwort`; dieser offene Zweittrigger muss über einen späteren,
harmonischen Upgrade-Schritt erworben werden.

### Drei Leitfamilien aus klassischen TCG-Funktionen

`formation_amplifier` übernimmt die Designrolle von Effekten, die eine einzelne
Figur durch ihre sichtbare Formation stärken. Die kleinste Form zählt nur
andere offene eigene Figuren und besitzt ein enges Bonuscap. Höhere Stufen
dürfen zusätzlich DEF, Nachbarschaft oder eine verbundene Figur einbeziehen;
sie dürfen niemals durch beliebige Token oder verdeckte Information
unkontrolliert skalieren.

`revealing_stasis` verbindet Information und Tempo: Eine kleine Form deckt ein
Ziel auf oder sperrt dessen nächsten Angriff. Eine mittlere Form kann beides in
einer Linie verbinden. Eine hochstufige Form darf mehrere gegnerische Figuren
aufdecken und ihre nächste Angriffsphase teilweise blockieren. Eine vollständige
Sperre der gegnerischen Formation ist mindestens Ultra, zeitlich eng begrenzt,
reaktionsfähig und mit Kosten oder einem Once-per-match-Limit versehen.

`symmetric_collapse` ist die Feldräumungsfamilie. Niedrige Varianten tauschen
die Quelle gegen genau ein Ziel oder räumen eine einzelne Linie. Rare und Super
dürfen Reihen oder Modi adressieren. Erst Ultra oder Legendary darf nahezu das
gesamte Feld betreffen; dabei bleiben Symmetrie, erhebliche Kosten, ein offenes
Reaktionsfenster und höchstens eine Nutzung pro Match verbindlich. Der
Legendary-Capstone darf die Asymmetrie nicht kostenlos entfernen.

### Komplexitätsleiter innerhalb einer TraitLineage

Die Komplexität steigt kontrolliert und nicht nur über größere Zahlen:

| Stufe | Zulässige Grundform pro Trait |
|---|---|
| Common | ein Trigger, ein einfacher Zielselektor, ein Opcode und ein klarer Endzeitpunkt |
| Uncommon | zusätzlich eine Bedingung oder ein zweiter eng gekoppelter Opcode |
| Rare | charakteristische Zwei-Schritt-Wirkung, gebundene Instanz oder Zählermechanik mit sichtbarer Schwelle |
| Super | breiterer Linien-/Reihenscope oder ein schwächerer alternativer Trigger innerhalb desselben Stamms |
| Ultra | starke Timingflexibilität, Trait-Synergie oder Formationswirkung bei expliziter Kosten- und Counterplay-Steigerung |
| Legendary | einmaliger Capstone des Ankertraits; großer Payoff, aber feste Kosten, Limit, Scope und Reaktionsmöglichkeit |

Ein neuer Trigger ist damit selbst eine bezahlte Upgradeachse. Eine Karte darf
nicht gleichzeitig Reichweite, Dauer, Zahlen, Geschwindigkeit, Triggerzahl und
Nutzungszahl maximieren. Ein alternativer Trigger muss dieselbe Kernwirkung
tragen: Eine Ambush-Linie kann etwa später auch beim offenen Angegriffenwerden
einen schwächeren Schutz auslösen, aber nicht unvermittelt Kartenziehen oder
Direktschaden ergänzen.

## Effektbudget v0.1

Jede aktuelle Kartenrevision besitzt ein kumulatives `effect_budget`. Bezahlt
wird der vollständige gegenwärtige Zustand aller Traits, nicht noch einmal jede
historische Zwischenrevision. Die Summe der Nettokosten aller Traits muss im
rarity- und levelabhängigen Zielkorridor liegen. Ein Level Up muss die
Nettokosten um mindestens einen Punkt erhöhen und weiterhin genau eine primäre
Trait-Aktion ausführen.

Der Randomizer zieht den konkreten Zielwert reproduzierbar aus dem geschlossenen
Intervall. Ein Ergebnis außerhalb des Intervalls wird nicht durch Prosatext
repariert, sondern deterministisch neu materialisiert.

| Entwicklungsstand | Budgetcap | zulässige Nettokosten der Karte |
|---|---:|---:|
| Standard | 0 | 0 |
| Common L1 | 4 | 4 |
| Common L2 | 5 | 5 |
| Common L3 | 6 | 6 |
| Uncommon L1 | 9 | 8–9 |
| Uncommon L2 | 10 | 9–10 |
| Uncommon L3 | 11 | 10–11 |
| Rare L1 | 14 | 12–14 |
| Rare L2 | 15 | 13–15 |
| Rare L3 | 16 | 14–16 |
| Super L1 | 21 | 18–21 |
| Super L2 | 23 | 20–23 |
| Super L3 | 25 | 22–25 |
| Ultra L1 | 31 | 27–31 |
| Ultra L2 | 34 | 29–34 |
| Ultra L3 | 37 | 32–37 |
| Legendary Capstone | 45 | 39–45 |

Damit liegt der Mindestwert eines neuen Rarity-Tiers grundsätzlich über dem
Cap des vorherigen Tiers. Die größere Streuung ab Rare erzeugt Varianz, ohne
eine niedrigere Rarity mechanisch an der nächsthöheren vorbeiziehen zu lassen.

### Kostenformel

```text
gross_trait_cost = timing
                 + trigger
                 + target_scope
                 + opcode_payload
                 + magnitude
                 + duration
                 + frequency_and_flexibility

net_trait_cost = gross_trait_cost - admitted_constraint_credits
card_net_cost  = sum(net_trait_cost aller aktuellen Traits)
```

Jeder Trait muss mindestens einen Nettopunkt kosten. Eng gekoppelte zweite
Opcodes zahlen ihre normalen Opcodekosten plus einen Kombinationspunkt.
Auswahl zwischen zwei verschiedenen Auflösungen kostet zusätzlich zwei Punkte.
Eine nicht zielende Flächenwirkung kostet zusätzlich einen Punkt; verwendet
sie Zerstörung, Negate oder Angriffssperre, kommen weitere drei
`area_impact`-Punkte hinzu.

#### Timing- und Triggerkosten

| Achse | Kosten |
|---|---:|
| Geschwindigkeit 0, passive/source-bound Aura | 1 |
| Geschwindigkeit 1 | 0 |
| Geschwindigkeit 2 | 2 |
| Geschwindigkeit 3, Counter | 4 |
| `on_play_face_up` oder `activated_main_phase` | 0 |
| einfacher Ereignistrigger wie Reveal, offen angegriffen, Angriff, Kampfresultat, Zerstörung, Opfer oder Zuggrenze | 1 |
| unmittelbar angegriffen, während die Karte verdeckt war | 1 |
| Schwelle aus `N` vollständig aufgelösten Angriffen | 2 |
| jeder zusätzliche alternative Trigger desselben Traits | Triggerkosten des Fensters plus 2 Flexibilitätspunkte |

`on_armed_reveal` verwendet den einfachen Reveal-Trigger und kann für die
vollständige Vorbereitungsrunde genau einen Constraint Credit erhalten. Der
Credit bezahlt die tatsächliche Verzögerung, nicht das Überraschungsmoment.

#### Ziel- und Scopekosten

| Scope | Kosten |
|---|---:|
| Quelle selbst oder durch Ereignis eindeutig gebundene Quelle/Angreifer/Ziel | 0 |
| ein frei gewähltes gültiges Ziel | 1 |
| ein gewähltes benachbartes Ziel oder ein Ziel derselben Linie | 1 |
| bis zu zwei Ziele oder ein festes Nachbarpaar | 2 |
| alle Figuren genau einer Linie | 3 |
| eine Front-/Back-Reihe oder alle eigenen Figuren in einem eng begrenzten Scope | 4 |
| alle eigenen Figuren | 5 |
| alle gegnerischen Figuren | 6 |
| beide vollständigen Felder oder ein globaler Zustand | 8 |

#### Opcodekosten

| Opcodefamilie | Grundkosten |
|---|---:|
| aufdecken, Kampfmodus ändern, ATK oder DEF verändern | 1 |
| bewegen, einen normalen Angriff beschränken, nächsten direkten Angriff abschirmen | 2 |
| eine Zerstörung verhindern, einen Angriff negieren, eine Karte ziehen oder kontrolliert zurückholen | 3 |
| eine Figur zerstören, auf die Hand geben, einen Trait/Opcode negieren oder eine Handkarte erzwingen | 4 |
| eine Figur wiederbeleben/direkt ausspielen oder genau einen Zusatzangriff gewähren | 5 |
| Kontrolle einer gegnerischen Figur übernehmen | 6 |
| unmittelbaren LP-Schaden verursachen oder heilen | 1 plus Magnitudekosten |

Mehrere gezogene Karten bezahlen die Drawkosten für jede Karte. Ein
Flächen-Opcode bezahlt seine Grundkosten einmal sowie Scope-, Non-target- und
gegebenenfalls Area-impact-Kosten. Zerstörung, Opfer, Rückgabe, Negate und
Entfernung bleiben verschiedene Opcodes und können nicht unter einem billigen
Sammelbegriff materialisiert werden.

#### Magnitude-, Dauer- und Flexibilitätskosten

| Zahlenbetrag eines einzelnen Buffs, Debuffs, Schadens oder Heileffekts | Kosten |
|---|---:|
| 100–200 | 0 |
| 250–400 | 1 |
| 450–600 | 2 |
| 650–800 | 3 |
| 850–1.000 | 4 |
| 1.050–1.400 | 5 |
| 1.450–1.800 | 6; nur Legendary |

| Dauer oder Wiederholung | Kosten |
|---|---:|
| sofort oder nur für das aktuelle Kampfereignis | 0 |
| bis zum Ende des aktuellen Zuges oder der aktuellen Angriffsphase | 1 |
| bis zum Ende des nächsten relevanten eigenen/gegnerischen Zuges | 2 |
| über zwei feste Zuggrenzen | 3 |
| solange die offen angreifbare Quelle liegt oder bis eine einzelne Instanz verbraucht wird | 1 |
| dauerhaft für den Rest des Matchs | 4 |
| natürlicher Einmaltrigger oder once per match | 0 |
| einmal pro Zug | 1 |
| bei jedem passenden Ereignis ohne Once-per-turn-Grenze | 2 |
| zusätzliche Nutzung im selben Turnus | 1 je zusätzlicher Nutzung |

Dynamische Skalierung, etwa ein Bonus je eigener offener Figur, kostet einen
zusätzlichen Punkt und benötigt immer einen materialisierten Höchstwert. Ein
neuer alternativer Zielmodus kostet einen, eine Wahl zwischen zwei
unterschiedlichen Effektzweigen zwei Flexibilitätspunkte.

### Begrenzte Constraint Credits

Echte Nachteile dürfen eine stärkere Wirkung innerhalb desselben Rarity-Gates
finanzieren. Sie erzeugen keine negativen Traitkosten und schalten keine
verbotene Reichweite, Geschwindigkeit oder Opcodeklasse frei.

| Verbindliche Einschränkung/Kosten | maximaler Credit |
|---|---:|
| eine volle Runde ununterbrochen verdeckt vorbereiten | 1 |
| bestimmter Kampfmodus, Slot oder belegbare Positionsbedingung | 1 |
| Quelle erschöpfen | 1 |
| eine Handkarte ablegen | 2 |
| 500 LP zahlen | 1 |
| 1.000 LP zahlen | 2 |
| eigene Quelle opfern | 3 |
| eine weitere eigene Figur opfern | 3 |
| bis Zugende keine normalen oder direkten Angriffe erklären | 1 |

Credits derselben realen Einschränkung werden nur einmal gezählt. Wird die
Quelle geopfert, darf ihre anschließende Abwesenheit nicht zusätzlich als
Source-bound-Nachteil gutgeschrieben werden. Die maximal anrechenbaren Credits
lauten Common 1, Uncommon 2, Rare 3, Super 4, Ultra 5 und Legendary 6.

### Harte Rarity-Gates

Punkte allein reichen nicht. Die folgende Tabelle verhindert, dass eine
Common-Karte durch viele Nachteile zufällig einen Legendary-Effekt erhält.

| Rarity | maximaler regulärer Scope und freigeschaltete Komplexität |
|---|---|
| Common | selbst oder ein Ziel; ein Opcode; Speed 2 nur als Reaktion, die unmittelbar diese Figur oder ihren Angreifer betrifft; kein Opcode, der eine gegnerische Figur zerstört oder einen gegnerischen Trait negiert |
| Uncommon | bis zu zwei eng gekoppelte Ziele; einzelnes Destroy/Return/Draw/Protection mit Bedingung oder Kosten; kein Speed-3-Counter |
| Rare | vollständige Linie; Zwei-Schritt-Wirkung, gebundene Instanz oder sichtbare Angriffsschwelle; Zusatzangriff oder Wiederbelebung nur eng begrenzt |
| Super | Reihe oder alle eigenen Figuren; bedingte Flächenwirkung; erster gezielter Speed-3-Counter; schwächerer alternativer Trigger möglich |
| Ultra | vollständige gegnerische Seite; genau eine gegnerische Angriffsphase vollständig sperrbar; symmetrischer Whole-field-Collapse nur mit Registry-Ausnahme, erheblicher Zahlung und once per match |
| Legendary | globaler Scope und Capstone-Rider; weiterhin höchstens eine vollständige gegnerische Angriffsphase sperren, stattdessen zusätzliche Synergie oder Information kaufen |

Source-bound passive Wirkungen sind in allen Rarities erlaubt, weil die offene
Quelle selbst das Counterplay bildet. Eine harte Angriffssperre über mehrere
vollständige gegnerische Angriffsphasen wird im MVP auch Legendary nicht
zugeteilt.

### Verbindliche Zahlenkorridore

Alle ATK-/DEF-Modifikatoren werden in 50er-Schritten materialisiert.

| Rarity und Level | einzelner statischer Buff/Debuff |
|---|---:|
| Common L1 / L2 / L3 | 100–200 / 150–300 / 200–400 |
| Uncommon L1 / L2 / L3 | 250–400 / 300–500 / 350–600 |
| Rare L1 / L2 / L3 | 400–600 / 450–700 / 500–800 |
| Super L1 / L2 / L3 | 600–800 / 650–900 / 700–1.000 |
| Ultra L1 / L2 / L3 | 800–1.100 / 900–1.250 / 1.000–1.400 |
| Legendary | 1.200–1.800 |

| Rarity | dynamischer Bonus je gültiger Figur | absolutes Cap | einmaliger LP-Schaden oder Heilung | maximales Ziehen |
|---|---:|---:|---:|---:|
| Common | 100 | 300 | 200 | 1, nur an Kosten/Ereignis gebunden |
| Uncommon | 100–150 | 450 | 400 | 1 |
| Rare | 150–200 | 600 | 600 | 2 mit Kosten |
| Super | 200–250 | 800 | 800 | 2 |
| Ultra | 250–300 | 1.000 | 1.200 | 3 mit Kosten |
| Legendary | 300–400 | 1.200 | 1.600 | 3 |

Ein wiederholbarer LP-Effekt darf höchstens die Hälfte des angegebenen
Einmalcaps verwenden. Ein einzelner Trait darf seinen Zahlenkorridor nicht in
mehreren parallelen Buffs umgehen; gekoppelte ATK- und DEF-Boni teilen sich das
Magnitudebudget.

### Randomizergewichte für Entwicklung

Die erste Common-Fähigkeit verwendet folgende Ausgangsgewichte; nicht
freigeschaltete Familien besitzen Gewicht null:

| erster Trait-Stamm | Gewicht |
|---|---:|
| `formation_amplifier` | 18 % |
| `revealing_stasis` | 12 % |
| `veiled_ambush` | 18 % |
| `open_guard` | 18 % |
| `battle_momentum` | 12 % |
| `bound_support` | 12 % |
| `sacrifice_exchange` | 5 % |
| `line_control` | 5 % |
| `symmetric_collapse` / `counterseal` | 0 % als erster Common-Trait |

Collection Coverage darf ein Gewicht um höchstens fünf Prozentpunkte
verschieben; danach wird der zulässige Pool auf 100 Prozent normalisiert. Sie
darf weder Rarity-Gates noch Trait-Harmonie umgehen. `symmetric_collapse` wird
frühestens Rare als kompatible Fortsetzung von Sacrifice/Line Control,
`counterseal` frühestens Super als Fortsetzung von Guard/Support freigeschaltet.

Besitzt die Karte einen freien Trait-Slot, gelten für die primäre Trait-Aktion
folgende Ausgangsgewichte:

| Entwicklungsschritt | neuer kompatibler Trait | vorhandenen Trait steigern |
|---|---:|---:|
| Standard → Common L1 | 100 % | 0 % |
| Common L2/L3 | 0 % | 100 % |
| Uncommon L1, zweiter Slot öffnet | 60 % | 40 % |
| weitere Uncommon-/Rare-Schritte mit freiem zweiten Slot | 30 % | 70 % |
| Super L1, dritter Slot öffnet | 55 % | 45 % |
| weitere Super-/Ultra-Schritte mit freiem dritten Slot | 20 % | 80 % |
| Trait-Cap erreicht | 0 % | 100 % |
| Legendary | 0 % | 100 % Anker-Capstone |

Führt die gezogene Aktion zu keinem harmonischen, budgetgültigen Kandidaten,
verwendet der Randomizer die andere Aktion und persistiert den Fallback im
Receipt. Ein Favorite auf Rare L1 simuliert die Schritte ab Common nacheinander
mit denselben Gewichten. Championtitel und weitere qualifizierte Siege setzen
die vorhandene Revision fort und würfeln keinen neuen Stamm.

### Beispielhafte Budgetbelege

```text
Common L1 · Standhafte Antwort
Speed 2 (2) + offen angegriffen (1) + eventgebundenes Ziel (0)
+ DEF ändern (1) + 100–200 (0) + aktuelles Kampfereignis (0)
= 4 Nettopunkte

Rare · Enthüllende Ruhe als ein Trait einer Zwei-Trait-Karte
Reveal-Trigger (1) + gewähltes Ziel (1) + Reveal (1)
+ Angriffssperre (2) + zweiter Opcode (Kombinationspunkt 1)
+ bis Ende des nächsten relevanten Zugs (2)
= 8 Nettopunkte; restliches Kartenbudget liegt im harmonischen zweiten Trait

Ultra · Leeres Feld
globaler Scope (8) + nicht zielend (1) + Destroy (4)
+ destructive area impact (3) = 16 brutto
- Quelle opfern (3) - keine direkten Angriffe (1) = 12 netto
Nur das Ultra-Registry-Gate erlaubt den symmetrischen Whole-field-Opcode;
weitere Traits und Upgrades müssen die Karten-Nettokosten auf 27–31 bringen.
```

## EffectInstance-Cap und Stacking

Jedes konkrete Bindungsziel besitzt höchstens drei gleichzeitig aktive,
fortdauernde `EffectInstances`. Als Bindungsziele gelten eine Figureninstanz,
ein Spieler, eine Linie oder der Matchzustand jeweils getrennt. Das Limit gilt
also nicht dreimal je Effektfamilie, sondern insgesamt je Zielobjekt.

Bei einer Figurenkarte zählen nicht als belegte EffectInstance:

- ihre bis zu drei eigenen Traitdefinitionen,
- sofort vollständig aufgelöste Einmaleffekte,
- Kettenglieder, die noch keine fortdauernde Wirkung erzeugt haben,
- Regelzustände wie offen/verdeckt, Angriff/Verteidigung,
  Einsatzverzögerung oder verbrauchte Angriffe,
- sowie traitinterne Zähler und Limits wie `armed`, Angriffszähler oder
  once-per-turn-Nutzung.

Erzeugt ein eigener oder fremder Trait dagegen einen zeitlich fortdauernden
Buff, Debuff, Ward, Lock, gebundenen Support oder eine Aura-Projektion auf der
Figur, belegt diese Bindung genau einen der drei Plätze. Mehrere eng gekoppelte
Opcodes derselben Wirkung – etwa `+ATK`, `+DEF` und Zerstörungsschutz aus einem
einzigen Schutzbund – bleiben eine EffectInstance. Derselbe Trait auf zwei
Zielen erzeugt je Ziel eine eigene Instanz.

### Stacking Key

Jede Instanz besitzt einen serverseitig materialisierten `stacking_key` aus
Wirkungsgruppe, betroffenem Wert/Zustand und Blueprint-Linie. Positive und
negative Wirkungen besitzen getrennte Keys. Damit blockiert ein eigener Buff
nicht die gleichnamige gegnerische Schwächung.

Trifft eine neue Instanz auf denselben `stacking_key`, entsteht kein vierter
oder doppelter Stapel:

1. Die stärkere regelgültige Instanz ersetzt die schwächere am bestehenden
   Platz.
2. Bei gleicher Stärke wird nur dann die Dauer erneuert, wenn der Blueprint
   `refresh_allowed = true` besitzt.
3. Ist die neue Instanz schwächer oder ein Refresh verboten, verpufft ihre
   fortdauernde Wirkung; bereits bezahlte Kosten werden nicht erstattet.

`formation_amplifier`-Quellen derselben Blueprint-Linie addieren sich daher
nicht beliebig. Unterschiedliche harmonische Keys dürfen sich bis zum
Dreierlimit algebraisch ergänzen.

### Vierte Instanz

Sind drei unterschiedliche Keys aktiv und soll eine vierte fortdauernde
Instanz entstehen, wird vor ihrer Bindung die älteste aktive Instanz dieses
Ziels anhand ihrer serverseitigen `creation_sequence` entfernt. Danach wird die
neue Instanz als jüngste gebunden. Im MVP existieren keine nicht ersetzbaren
oder „gelockten“ EffectInstances.

Die Verdrängung ist automatisch und nicht wählbar. Dadurch kann ein Spieler
seine Figur nicht mit drei kleinen positiven Effekten gegen einen gegnerischen
Debuff immunisieren; umgekehrt kann ein neuer eigener Buff auch einen alten
Debuff verdrängen, wenn dieser tatsächlich die älteste Bindung ist. Eine
optionale Aktivierung darf vor der Kostenzahlung unterlassen werden. Sobald sie
aktiviert wurde, gehören Kosten, möglicher Same-key-Fizzle und FIFO-Verdrängung
zur bekannten Vorschau.

### Auren und Neuberechnung

Eine Aura erzeugt je betroffenem Ziel eine stabile `aura_projection` und belegt
dort einen Platz. Solange Quelle, Position und Bedingung unverändert bleiben,
wird ihre `creation_sequence` bei Neuberechnung nicht erneuert. Verliert die
Aura ihre Bedingung, endet die Projektion sofort. Wird das Ziel später erneut
gültig, entsteht eine neue jüngste Projektion und kann nach derselben
FIFO-Regel eine alte Instanz verdrängen.

Linien- oder spielergerichtete Locks werden nur am eigentlichen Linien- oder
Spielerobjekt gespeichert und nicht zusätzlich auf jede betroffene Figur
kopiert. Ein globaler Effekt belegt entsprechend einen Matchplatz. Das hält die
Obergrenze semantisch stabil und verhindert künstliche Mehrfachzählung.

### Verrechnung numerischer Instanzen

Der MVP verwendet zunächst ausschließlich additive ATK-/DEF-Modifikatoren:

```text
aktueller Wert = max(0,
  Grundwert
  + intrinsische offene Traitmodifikatoren
  + Summe der höchstens drei gebundenen additiven EffectInstances)
```

Positive und negative Modifikatoren werden anhand ihrer stabilen
`creation_sequence` protokolliert, mathematisch aber als eine atomare Summe
angewendet. Temporäre Effekte dürfen dadurch weiterhin den Legendary-Korridor
überschreiten. Prozent-, Verdopplungs-, Halbierungs- und Set-to-value-Opcodes
gehören nicht zum initialen Registry-Schnitt; ihre spätere Einführung benötigt
eine eigene Layer-Reihenfolge.

### Beispiel: harmonische Ambush-Entwicklung

```text
Common
→ Wenn diese verdeckte Karte angegriffen wird: decke sie auf und senke den
  Angriff des Angreifers bis zum Ende des Kampfereignisses.

Uncommon
→ Der Debuff wird stärker, falls die Karte bereits armed war.

Rare
→ Nach einer vollständig verdeckt überstandenen Runde darf sie den Angriff
  zusätzlich abbrechen; der Reveal-only-Angriff bleibt trotzdem beendet.

Super
→ Der Konter darf stattdessen eine benachbarte eigene Figur schützen.

Ultra
→ Einmal pro Zug kann dieselbe Kernreaktion auch beim offenen Angegriffenwerden
  in abgeschwächter Form ausgelöst werden.

Legendary
→ Once per match schützt der armed Reveal die eigene Linie und versetzt den
  Angreifer in Verteidigung; Negate und Entfernung der Quelle bleiben möglich.
```

Die Zahlen und konkrete Zielauswahl dieses Beispiels werden vom Budget gezogen.
Die erkennbare Identität bleibt durchgehend „vorbereiteter Hinterhalt und
Schutzreaktion“.

## Struktur einer ausführbaren Fähigkeit

Jede materialisierte Fähigkeit besteht mindestens aus:

```text
CardAbilityRevision
├─ ability_family
├─ trigger
├─ conditions[]
├─ target_selector
├─ effects[]
│  ├─ registered_opcode
│  ├─ magnitude
│  └─ affected_value_or_state
├─ duration
├─ activation_costs[]
├─ usage_limit
├─ visibility_policy
├─ timing_priority
├─ counterplay_tags[]
├─ effect_budget_receipt
└─ rules_version
```

Die Grundachsen sind unabhängig kombinierbar:

| Achse | Beispiele |
|---|---|
| Auslöser | `on_play`, `on_reveal`, `on_attacked`, `on_attack`, `on_destroyed`, `turn_start` |
| Ziel | selbst, eigene Figur, gegnerische Figur, Nachbar, Linie, eigener Spieler, Gegner |
| Wirkung | Wert ändern, Schaden, heilen, ziehen, ablegen, aufdecken, Modus wechseln, bewegen, negieren |
| Dauer | sofort, bis Zugende, bis nächster Angriff, solange offen, feste Zugzahl |
| Kosten | erschöpfen, opfern, Moduswechsel, Handkarte, einmal pro Zug/Match |
| Gegenwehr | verhindern, Ziel ungültig machen, Quelle entfernen, Reveal erzwingen, Timing kontern |

Nicht jede technisch denkbare Kombination ist zulässig. Eine versionierte
Compatibility Matrix verhindert unauflösbare Ziele, widersprüchliche Dauer,
verdeckte Endlosschleifen, unbegrenzte Rekursion und Wirkungen außerhalb des
Raritybudgets.

## Kontrollierter Zufall und LLM-Kontextualisierung

Die LLM bestimmt die Fähigkeit nicht. Sie erhält eine vollständig
materialisierte strukturierte Regel und übersetzt deren Bedeutung in den
Kontext des Bildes. Der Ablauf lautet:

Der serverseitige Randomizer arbeitet gestuft und reproduzierbar:

1. Rarity und Level bestimmen getrennte Werte- und Effektbudgets.
2. Das Wertebudget wird innerhalb zulässiger Korridore auf Angriff und
   Verteidigung verteilt.
3. Das Effektbudget zieht Fähigkeitsfamilie und Effektform.
4. Danach werden kompatible Trigger, Bedingungen, Ziele, Opcodes, Dauer,
   Kosten und Nutzungslimits gezogen.
5. Eine Compatibility Matrix verwirft unzulässige Kombinationen und verwendet
   den nächsten deterministischen Wurf desselben Receipts.
6. Erst die vollständig validierte Fähigkeit erreicht die LLM.

```text
CardIdentity, Branding, Bildbeschreibung, Rarity und Level
→ Server zieht reproduzierbar Effektbudget und vollständige strukturierte Fähigkeit
→ Validator prüft Budget, Loop, Target und Timing
→ LLM formuliert bildbezogenen Namen, verständliche Effekterklärung und Flavor
→ Validator prüft semantische Deckung mit der feststehenden Regel und Canon-Grenze
→ Materializer schreibt immutable CardAbilityRevision und Random Receipt
```

Der serverseitige Zufall lässt der LLM keine offenen mechanischen Choice Slots.
Trigger, Ziel, Wirkung, Dauer, Kosten, Limit und Zahlen stehen vor dem
LLM-Aufruf fest. Die LLM darf anhand der Bildbeschreibung erklären, weshalb
beispielsweise ein geöffneter Regenschirm den bereits bestimmten Schutzbonus
repräsentiert. Sie darf keinen Trigger, kein Ziel, keine Wirkung und keine Zahl
ergänzen, austauschen oder auslassen.

Der verbindliche kurze Regeltext wird zusätzlich deterministisch aus der
CardAbilityRevision gerendert. Die LLM erzeugt Kartenname, bildbezogene
Beschreibung und Flavor sowie optional eine leichter lesbare Erklärung
desselben Effekts. Besteht diese Erklärung die semantische Deckungsprüfung
nicht, wird sie verworfen und ausschließlich der deterministische Regeltext
angezeigt. Spielsimulation und Spielerentscheidung hängen deshalb niemals von
einer kreativen Formulierung ab.

Das LLM-Ergebnis wird persistiert und im Replay nicht neu erzeugt. Gleicher
Craft Seed und gleiche Regelrevisionen müssen denselben autoritativen
Materialisierungsbeleg reproduzieren; eine spätere Modelländerung verändert
keine existierende Karte.

## Effektgeschwindigkeit und Reaktionsketten

Effekte besitzen eine von vier Timingklassen:

| Geschwindigkeit | Effektform | Timingregel |
|---:|---|---|
| `0` | passiv oder dauerhaft | gilt automatisch bei erfüllter Bedingung und erzeugt kein Kettenglied |
| `1` | normal, aktiviert oder langsamer Trigger | startet im eigenen zulässigen Aktionsfenster eine Kette, darf aber nicht als freie Reaktion angehängt werden |
| `2` | schnell, reaktiv oder Falle | darf in einem passenden Reaktionsfenster auf Aktionen und langsamere beziehungsweise gleich schnelle Effekte antworten |
| `3` | Konter | antwortet unmittelbar auf das vorherige Kettenglied; auf einen Konter darf nur ein weiterer Konter folgen |

Automatische Trigger werden je nach Blueprint als Geschwindigkeit 1 oder 2
materialisiert. Passive Neuberechnungen sind Geschwindigkeit 0 und öffnen
nicht bei jeder Änderung erneut eine Kette.

Der gemeinsame Kettenablauf lautet:

1. Eine Aktion, Aktivierung oder ein Ereignis eröffnet ein zulässiges
   Reaktionsfenster.
2. Die Gegenseite erhält zuerst die Möglichkeit zu reagieren; danach wechseln
   sich beide Parteien mit genau einer Reaktion oder Passen ab.
3. Nach zwei aufeinanderfolgenden Pässen wird die Kette nach dem
   Last-in-first-out-Prinzip vollständig rückwärts aufgelöst.
4. Ziele und Kosten werden bei Aktivierung gebunden. Bezahlte Kosten werden
   auch bei Negierung oder später ungültigem Ziel nicht erstattet.
5. Wird ein gebundenes Ziel vor seiner Auflösung ungültig, verpufft die darauf
   gerichtete Wirkung gemäß ihrer strukturierten Fizzle-Regel.
6. Während ein Kettenglied aufgelöst wird, darf kein neuer Effekt
   dazwischengeschoben werden. Neu entstehende Trigger warten bis zur
   vollständigen Auflösung und eröffnen danach gegebenenfalls eine Folgekette.
7. Nach jedem vollständig aufgelösten Kettenglied prüft die Simulation atomar
   die Niederlagebedingungen. Ein terminales Ergebnis beendet das Match und
   verwirft verbleibende Kettenglieder. Sonstige Zustandsprüfung, Zerstörung und
   Ermittlung neuer Pflichttrigger erfolgen nach der gesamten fortbestehenden
   Kette.

Ein optionales Reaktionsfenster wird dem Spieler nur als Interaktion
projiziert, wenn mindestens eine legale Reaktion existiert. Ohne legale Wahl
passt der Server automatisch. Existiert eine Wahl, bleibt das Fenster ohne
Zugzeitlimit revisionsgebunden fortsetzbar.

Eine Kette besitzt höchstens sechs Kettenglieder. Ist das Limit erreicht,
dürfen keine weiteren optionalen Reaktionen aktiviert werden. Zwingende
Trigger gehen nicht verloren, sondern werden deterministisch in die nächste
Folgekette gestellt. Unbegrenzte Selbsttrigger, zirkuläre Wiederaktivierung und
Regelkombinationen ohne sinkendes Ausführungsbudget sind ungültig.

Der erste normale Angriff auf eine verdeckte Karte bleibt unabhängig von der
Kette ein reiner Aufdeckangriff. Reveal- und Falleneffekte dürfen reagieren;
nach ihrer Auflösung entsteht aus demselben Angriff aber kein normaler
Angriffs-/Verteidigungsvergleich.

## Entwicklung von Common bis Legendary

Das erste Level Up zieht einen mechanischen Trait-Stamm. Dieser bleibt die
erkennbare Identität der Karte und wird nicht bei jeder Promotion vollständig
neu ausgewürfelt.

```text
Common
→ erster kleiner, klar lesbarer Trait

Uncommon
→ Trait-Upgrade oder zweiter harmonischer Trait

Rare
→ ausgeprägter Signature-Stamm aus höchstens zwei Traits; Favorite startet mindestens hier

Super
→ starke Upgrades oder höchstens ein dritter harmonischer Trait

Ultra
→ verstärkte Synergie der vorhandenen Traits

Legendary
→ Capstone-Upgrade des mechanischen Ankertraits
```

Der Legendary-Capstone wird nur materialisiert, wenn neben der mechanischen
Entwicklung sowohl der versionierte visuelle Bewährungsnachweis als auch die
geforderte, anti-farm-geprüfte Battle Lineage vorliegen. Gewonnene Matches oder
Experience-Punkte allein umgehen dieses Gate nicht.

Höhere Rarity darf mehr Stärke, Reichweite, Dauer, Timingflexibilität oder
Effektsynergie kaufen. Sie darf nicht zugleich alle Dimensionen maximieren.
Auch Legendary benötigt ein festes Budget, eine Ausspielhürde, ein
Nutzungslimit und regelgültige Gegenwehr.

Eine direkt als Favorite materialisierte Rare-Karte erhält deterministisch die
nicht ausgespielte Common-/Uncommon-Entwicklungshistorie, damit ihre Traits
trotz des Sprungs aus derselben TraitLineage entstehen.

## Beispiel einer Bildbindung

Eine Bildbeschreibung erkennt eine Figur mit geöffnetem Regenschirm vor einer
anderen Person. Der Randomizer hat bereits eine vollständige
Reveal-/Support-Regel mit begrenzter Schutzwirkung materialisiert. Die LLM darf
diese feste Entwicklungslinie beispielsweise über das Regenschirmmotiv
verständlich machen:

```text
Common: Beim Aufdecken erhält diese Karte kurzzeitig zusätzliche Verteidigung.
Rare: Beim Aufdecken schützt sie zusätzlich eine benachbarte eigene Figur.
Super: Der Schutz kann stattdessen den ersten Angriff auf diese Figur abfangen.
Ultra: Abfangen und Verteidigungsbonus verstärken sich im rear_center.
Legendary: Ein einmaliger Capstone schützt die verbundene Formation,
           bleibt aber an Reveal, Position und Nutzungslimit gebunden.
```

Das sichtbare Motiv begründet die thematische Form. Es beweist weder einen
Regelfakt noch schreibt es der Figur im VN-Canon übernatürliche Fähigkeiten zu.

## Testbare Invarianten

1. Jede Fähigkeit gehört zu einer Figurenkarte und erzeugt keine getrennte
   Zauber-, Fallen-, Trainer-, Item- oder Supportkarte.
2. Jede ausführbare Wirkung verwendet ausschließlich registrierte Trigger,
   Targets, Opcodes, Dauern, Kosten und Limits.
3. Die LLM darf keine mechanischen Choice Slots auswählen. Ihre Erklärung muss
   Trigger, Ziel, Wirkung, Dauer, Kosten, Limit und Zahlen der materialisierten
   Regel vollständig erhalten.
4. Ein einmaliger Effekt endet nach seiner Auflösung; eine dauerhafte Wirkung
   besitzt eine prüfbare Endbedingung.
5. Ein auf eine andere Figur gelegter Effekt besitzt stabile Source-, Target-
   und AbilityRevision-Bindung.
6. Ein Falleneffekt beim Aufdeckangriff löst keinen normalen Kampf desselben
   Angriffs aus.
7. Eine verdeckte Karte erzeugt ohne ausdrückliches verborgenes Primitiv keine
   öffentliche Dauerwirkung.
8. Eine zauberartige Aktivierung entfernt die Figurenkarte nicht automatisch
   aus ihrem Slot.
9. Rarity-/Levelpromotion entwickelt eine erkennbare TraitLineage weiter
   und würfelt keine unverbundene Karte neu.
10. Legendary-Effekte besitzen trotz hoher Stärke Kosten, Nutzungslimit und
    Gegenwehr.
11. Replay verwendet den persistierten Materialisierungsbeleg und ruft die LLM
    nicht erneut auf.
12. Sichtbarer Kartentext und Flavor sind niemals ausführbarer Regelcode oder
    VN-Canon-Autorität.
13. Passive Effekte erzeugen keine Kettenglieder; aktivierte und reaktive
    Effekte beachten ihre festgeschriebene Geschwindigkeit.
14. Eine Kette löst nach zwei Pässen höchstens sechs Glieder rückwärts auf;
    Kosten bleiben bezahlt und während der Auflösung wird nichts eingefügt.
15. Neue Pflichttrigger oberhalb des Kettenlimits werden deterministisch in
    eine Folgekette verschoben und niemals verworfen.
16. Standardkarten besitzen ATK und DEF, aber keinen Trait und keinen
    ausführbaren Karteneffekt.
17. Jeder Level Up fügt den ersten beziehungsweise einen kompatiblen neuen
    Trait hinzu oder steigert einen vorhandenen Trait.
18. Common, Uncommon, Rare, Super, Ultra und Legendary besitzen höchstens 1,
    2, 2, 3, 3 beziehungsweise 3 Traits.
19. Legendary entwickelt einen vorhandenen Ankertrait zum Capstone und erzeugt
    keinen vierten unabhängigen Trait.
20. Level- und Rarityentwicklung bleibt in derselben validierten TraitLineage
    und erzeugt keine unverbundene Neuauswürfelung.
21. Die Mechanikauswahl findet vor und ohne semantische Bildinterpretation
    statt; das LLM benennt und erklärt nur das materialisierte Ergebnis.
22. Offenes Ausspielen ist kein Reveal und kann keinen `on_reveal`- oder
    `on_armed_reveal`-Trigger erfüllen.
23. `on_attacked_while_face_down` prüft den Vorzustand, bevor die Karte
    aufgedeckt wird; der Angriff bleibt Reveal-only.
24. Ein Trait mit voller Fallenbereitschaft wird nur nach einer ununterbrochen
    verdeckt überstandenen Runde `armed`.
25. Angriffszähler zählen vollständig aufgelöste Angriffe; negierte oder vor
    ihrer Auflösung abgebrochene Angriffe erhöhen sie nicht.
26. Der Starter-Mechanikraum besteht mindestens aus Formationsverstärkung,
    Reveal-Stasis, symmetrischer Feldräumung, Ambush, offenem Schutz,
    Angriffsmomentum, gebundenem Support, Counterseal, Sacrifice-Austausch und
    Linienkontrolle.
27. Eine höhere Stufe darf neue Trigger oder größere Scopes nur als bezahlte
    Upgradeachse derselben harmonischen TraitLineage erhalten.
28. Nach jedem Kettenglied wird Matchende geprüft; ein terminales Ergebnis
    beendet die weitere Kettenauflösung.
29. Ein optionales Reaktionsfenster ohne legale Spielerreaktion wird
    serverseitig automatisch gepasst und erzeugt keinen leeren Pflichtdialog.

## Post-v0.1-Erweiterungen und Playtestkalibrierung

- Erweiterung der initialen Registry um spätere, ausdrücklich versionierte
  Opcodes und Trigger,
- post-Playtest-Anpassung der initialen Budgets, Zahlenkorridore,
  Familiengewichte und Constraint Credits,
- eine spätere Layer-Reihenfolge für Prozent-, Verdopplungs-, Halbierungs- und
  Set-to-value-Opcodes,
- sowie visuelle Darstellung gebundener Effekte, Status, Triggerblöcke und
  Gegenwehr.

Diese Punkte verändern die abgeschlossene Effektgrammatik v0.1 nicht.
Registry-Erweiterungen und nicht additive Zahlenlayer benötigen eine neue
versionierte Regelrevision; Budget- und Häufigkeitswerte bleiben
Playtestkalibrierung.
