# Network-first VN-Frontend und Screen Map

> **DOKUMENTSTATUS: SOURCE_MATERIAL – NICHT VERBINDLICH.** Vollständige importierte Quellenfassung vom 2026-10-09. **Nicht** der aktuelle Code-Ist-Zustand, **kein** genehmigter Implementierungsplan und **keine** verbindliche Character-Chronicles-Architektur. Frühere Angaben wie „Autorität“, „DECIDED“, „Baseline abgeschlossen“ und „implementiert“ sind **historischer Originalwortlaut**.

**Quellkategorie:** `PRODUCT_VISION_WITH_OLD_UI_ASSUMPTIONS`  
**Worum es geht:** Network-first-UI und späterer VN-Welt-/Bildschirmaufbau, noch kein aktueller Navigationsvertrag.  
**Aktueller Referenzpunkt:** [bereinigter Überblick](../vision/social-network.md) · [Quellenindex](README.md) · [Entscheidungsregeln](../../DECISION_POLICY.md).

## Übernommene Quellenfassung (historischer Entwurf, keine aktuellen Beschlüsse)

**Ab hier folgt der damalige Text einschließlich seiner früheren Status- und Architekturbehauptungen.** Diese dürfen nicht ohne neue Codeprüfung/ausdrückliche Entscheidung in aktive Arbeitsaufträge umgedeutet werden.

---

Dokumentrolle: verbindlicher Zielrahmen für die spielerseitige Screen-Architektur

Autorität: Ergänzung der Frontend-Informationsarchitektur für den post-M6-Ausbau

Stand: 14. September 2026

## Zweck und Abgrenzung

Dieses Dokument übersetzt das Gesamtspiel in konkrete Oberflächen. Es definiert
nicht den gesamten Inhalt jeder Szene und keine endgültigen Eigennamen der
Plattform. Die Screen-IDs sind stabile Planungsbezeichner und keine zwingende
Spielercopy.

Der aktuelle M6-Schnitt beweist ausschließlich, dass Bilder in wiederholten
Zyklen generiert, durch Bildspiele bewertet und auf Grundlage der gewonnenen
Evidence verbessert werden. Social Feed, Chats, Tagesplanung, Orte, Deckbau und
Card-Battler-Partien gehören nicht in diesen Beweis. Sie werden hier trotzdem
als Zielbild festgehalten, damit der M6-Schnitt visuell und strukturell in die
richtige Richtung wächst und keine spätere Sackgasse baut.

Dieser Ausbau heißt in diesem Dokument bewusst `post-M6`. Die formale Roadmap
verwendet `M7` bereits für LoRA-Outcome und New-Game-Plus-Lineage. Eine spätere
Neuordnung der Meilensteinnamen ist eine eigene Entscheidung und wird nicht
durch die Screen Map vorweggenommen.

## Spielerische Hierarchie

Erzählerische Priorität und Häufigkeit einer Oberfläche sind zwei verschiedene
Dinge:

1. Die Visual Novel mit Dating-Sim-Struktur ist der übergeordnete Kern des
   Spiels. Beziehungen, Szenen, Entscheidungen und der Verlauf beider Academy-Jahre
   liefern die langfristige Motivation.
2. Der aktuelle Ort ist der natürliche Hauptscreen zwischen ausgespielten
   VN-Szenen, sobald sein benötigtes Bildmaterial vorhanden und freigegeben ist.
3. Das Social Network ist das soziale Betriebssystem dieser Welt. Es ist zu
   Beginn aus Produktionsgründen die bildschirmfüllende Hauptoberfläche und
   später weiterhin die häufig genutzte Geräteansicht.
4. Der Card Battler ist ein Feature dieses Networks. Booster, Sammlung,
   Visual Circuit, Decks und Kämpfe bilden keinen vom Network losgelösten
   zweiten Launcher.
5. Trials sind die spielerischen Bewertungsruntimes innerhalb der Booster- und
   Kartenentwicklung. Sie bleiben fachlich eigenständig, werden im Zielspiel
   aber diegetisch aus dem jeweiligen Kartenkontext betreten.

Damit ist das Network weder der erzählerische Oberbau der VN noch bloß ein
kleines Menü. Die VN bestimmt, warum etwas wichtig ist; Ort und Network
bestimmen, von wo aus der Spieler im jeweiligen Zustand handelt.

## Drei dominante Canvas-Zustände

Zu jedem Zeitpunkt besitzt die Oberfläche genau einen dominanten Spielraum:

| Zustand | Wann er dominiert | Was darüber liegen darf |
|---|---|---|
| `network_fullscreen` | Zu Beginn, solange kein freigegebener Orts-Hub existiert; später beim bewussten Öffnen des Geräts | kleine globale Statuszeile, modale Bestätigung, kontextueller Drawer |
| `location_hub` | Zwischen VN-Szenen, sobald der aktuelle Ort als freigegebenes Visual Bundle vorliegt | kompakter Tages-/Ortsstatus, eine primäre Aktionsgruppe, Geräte- oder Planer-Overlay |
| `vn_scene` | Während ausgespielter Dialoge, Entscheidungen und authored Storymomente | Dialogbox, Namensschild, Choices und notwendige kleine Szenenindikatoren |

Feed, Deckbau, Kalender und Karte dürfen den Orts- oder VN-Spielraum nicht als
gleichzeitige Dauerpanels einengen. Textschwere Network- und Planerflächen sind
DOM-basiert. Im `location_hub` und in der `vn_scene` bleiben Mitte und untere
Bildhälfte für Hintergrund, Figuren und Dialog geschützt; seltene Informationen
liegen in Drawern oder eigenen Screens.

## Asset-gesteuerter Aufbau des VN-Rahmens

### Phase A – Network-first Bootstrap

Ein neuer Run besitzt noch keinen freigegebenen Home-Hintergrund und keine
fertigen Orts-Bundles. Die spielerseitige Runtime beginnt deshalb vollständig
im Network. Das ist innerhalb der Fiktion die Nutzung des eigenen Accounts im
neuen sozialen Umfeld und kein sichtbarer technischer Ersatzbildschirm.

Die Oberfläche darf in dieser Phase keinen generischen Raum, keine erfundene
Karte und keinen angeblich besuchbaren Ort vortäuschen. Sie zeigt nur
materialisierte Posts, Kontakte, Kartenanlässe und Systemfunktionen des aktuellen
Runs. Wie lang der Network-only-Prolog vor Schulbeginn dauert, bleibt offen und
wird nicht durch diesen Vertrag auf einen Monat festgelegt.

Dieser Zustand ist verbindlich die Spieleröffnung. Er ist keine `vn_scene` und
kein freigegebener `location_hub`. Feste ausgelieferte UI-/Silhouettenmittel sind
zulässig; save-spezifisch generierte Figuren-, Outfit-, Expression-, Place- oder
Background-Assets dürfen nicht vorausgesetzt werden. Die erste echte
`vn_scene` wird erst sichtbar, wenn ihr vollständiges Scene Presentation
Manifest aus freigegebenen Visual Bundles und AssetVersionen erfüllbar ist.

### Phase B – Home als erster Orts-Hub

Sobald das freigegebene Home-Bundle existiert, wird der eigene aktuelle Ort zum
Hauptscreen zwischen Szenen. Das Network wird von dort als Geräteansicht
geöffnet. Auf kleinen Displays darf diese Geräteansicht wieder den ganzen
Bildschirm belegen; auf großen Displays kann sie als klarer Vordergrundzustand
inszeniert werden. In beiden Fällen muss der Übergang verständlich machen, dass
der Spieler das Network am aktuellen Ort öffnet.

Ein minimales Orts-Bundle benötigt:

- einen freigegebenen Hintergrund mit Safe Areas für Dialog und HUD,
- eine stabile Ortsidentität und Tageszeitprojektion,
- erlaubte lokale Aktionen und Rückkehrverhalten,
- sowie einen klaren Fallback, falls eine optionale Figurendarstellung noch
  nicht vorliegt.

Ein freigegebener Orts-Hub garantiert keine VN-Szene. Er projiziert getrennt
lokale `PlaceActivityContract`s und tatsächlich spielbereite Scene Contracts.
Gerade im frühen Run darf der Hub Lernen, Erkundung, Erholung, Club- oder
Battler-Praxis und andere figurenbezogene Nicht-VN-Aktivitäten anbieten, obwohl
noch keine sichtbare Character-Begegnung möglich ist. Der Figurenbezug kann
remote, asynchron oder nur der bekannte konkrete Anlass sein. Fehlende
Character-, Outfit- oder Expression-Assets blockieren nur die betroffene
Aktivität beziehungsweise Szene und nicht den gesamten Ort. Network, Deck,
Kalender und Reise bleiben davon getrennte System- beziehungsweise
Navigationshandlungen.

### Phase C – Wachsende freigeschaltete Ortswelt

Weitere Kartenknoten und Orts-Hubs werden erst sichtbar beziehungsweise
betretbar, wenn ihr benötigtes Visual Bundle spielbereit ist. Die
Story-/Tagesplanung plant kommende Bedarfe vor und stößt ihre Produktion an,
bevor eine Szene oder Reise sie verbindlich benötigt. Ein noch nicht fertiges
Asset erscheint in der normalen Oberfläche nicht als ComfyUI-, Queue- oder
Providerfehler. Der Spieler bleibt in einem gültigen Network- oder Ortsfluss;
technische Details liegen ausschließlich in Advanced/Diagnose.

Nach einer VN-Szene führt der Standardrückweg zum aktuellen Orts-Hub. Existiert
dieser noch nicht oder wurde die Szene aus dem Network heraus inszeniert, führt
der Rückweg in den zuletzt gültigen Network-Kontext. Ein authored Folgeereignis
darf davon ausdrücklich abweichen.

## Konkrete Ziel-Screen-Map

### Network und soziale Identität

| ID | Screen | Primäre Spielerfrage | Hauptaktion |
|---|---|---|---|
| `NET-01` | Feed | Was passiert gerade in meinem Umfeld? | Post öffnen oder reagieren |
| `NET-02` | Post-Detail | Worum geht es genau und was kann daraus folgen? | reagieren, antworten oder verfügbaren Booster öffnen |
| `NET-03` | öffentliches Character-Profil | Was zeigt diese Figur im Network über sich? | Timeline ansehen, Nachricht öffnen oder erlaubte Verbindung wählen |
| `NET-04` | eigenes Profil | Wie trete ich im Network auf? | eigene sichtbare Inhalte und Plattformstatus prüfen |
| `NET-05` | Aktivität und Hinweise | Was hat sich seit meinem letzten Besuch verändert? | zur konkreten Nachricht, Karte, Storyfolge oder Einladung springen |
| `STR-01` | gefolgte Streams | Wer öffnet gerade oder zeitversetzt ein Pack, das ich sehen darf? | Stream beziehungsweise Aufzeichnung öffnen |
| `STR-02` | Community-Pack-Opening | Welche vier Kartenbilder zeigt der Streamer, und wie reagiere ich darauf? | Kandidaten ansehen, reagieren oder begründet melden |
| `STR-03` | Opening-Ergebnis | Wie hat der Besitzer entschieden, was sagt die Community und welche Event-Tickets habe ich erhalten? | Ergebnis einordnen oder öffentlichen Eventpfad öffnen |

Der Feed ist kein unendlicher generischer Contentstrom. Er projiziert nur
materialisierte, story- oder systemrelevante Inhalte des Runs und darf noch
unbekannte Figuren, Orte oder Konflikte nicht durch Metadaten leaken.

`STR-02` ist echter Network-Content und keine als Stream verkleidete
Moderationsmaske. Die vier Kandidaten, Streamchat-/Community-Projektion und
Reaktion bilden eine gemeinsame dominante Spielerfrage; technische Approval-,
Generation- und Evidencebegriffe bleiben außerhalb von Advanced. Eine separate
Meldeaktion muss dennoch jederzeit erreichbar sein. Die Besitzerentscheidung
darf sichtbar von der Reaktion des Protagonisten abweichen. Das Ergebnis erklärt
Event-Tickets als Zugang zu öffentlichen Events beziehungsweise Eventboostern
und verspricht weder die persönliche Karte des Streamers noch direkte
Kampfstärke.

### Direkte und gemeinsame Kommunikation

| ID | Screen | Primäre Spielerfrage | Hauptaktion |
|---|---|---|---|
| `MSG-01` | Nachrichtenübersicht | Wer hat mir geschrieben und was ist neu? | Thread öffnen |
| `MSG-02` | Einzelchat | Was sagt diese Figur mir privat? | Nachricht beziehungsweise Choice senden |
| `MSG-03` | Gruppenchat | Wie entwickelt sich die Situation in der Gruppe? | antworten, reagieren oder enthaltenen Anlass öffnen |
| `MSG-04` | Thread-Info | Wer gehört dazu und welche geteilten Inhalte kenne ich? | Mitglieder oder bekannte Medien prüfen |

Einzel- und Gruppenchats sind authored VN-Kommunikationsräume mit
Persistenzvertrag, keine freie Simulation ohne Storyautorität. Ihre visuelle
Metapher darf SMS- oder Messenger-Konventionen nutzen, bleibt aber Teil der
fiktiven Plattform.

### Kartenfeature innerhalb des Networks

| ID | Screen | Primäre Spielerfrage | Hauptaktion |
|---|---|---|---|
| `CARD-01` | Karten-Home | Was kann ich mit meinen Karten jetzt tun? | Booster, Sammlung, Visual Circuit, Deck oder Battle öffnen |
| `CARD-02` | Kartenbild gestalten | Welcher Ausschnitt des bestätigten Bildes gehört sichtbar in dieses Kartengesicht? | Bild hinter dem Frame verschieben, zoomen und Komposition bestätigen |
| `BST-01` | Booster-Herkunft | Woher kommt dieses Pack und welches Motiv trägt es? | Booster öffnen |
| `BST-02` | Booster-Opening | Welche vier neuen Kartenkörper erhalte ich? | vier Karten aufdecken und Bildspiel beginnen |
| `BST-03` | unmittelbares Ergebnis | Welche Spiel- und Bildkarten sind entstanden? | Resultate prüfen und den Flow verlassen |
| `BST-04` | finalisierte Kartenenthüllung | Wie wurden Name, Beschreibung und Darstellung vervollständigt? | Karte öffnen oder Sammlung ansehen |
| `COL-01` | Sammlung | Welche Karten besitze ich für diese Figur und insgesamt? | filtern, vergleichen oder Karte öffnen |
| `COL-02` | Kartendetail und Karriere | Was ist diese konkrete Spielkarte, welches Bild bindet sie und was hat sie erreicht? | Verwendung, Titel und Historie prüfen |
| `COL-03` | Character-Portfolio | Welche Bildkarten, Titel und Lücken gehören zu dieser Figur? | Visual Circuit oder passende Karte öffnen |
| `DECK-01` | Deckübersicht | Welche Decks sind spielbereit und wofür? | Deck wählen oder bearbeiten |
| `DECK-02` | Deckbau | Welche Karten erfüllen die Regeln und meine Strategie? | Deck ändern und validieren |
| `LIG-01` | Ligaübersicht | Wo stehe ich in Ranked, aktueller Liga und Qualifikation? | Saison, Tabelle oder nächsten Wettbewerb öffnen |
| `LIG-02` | Liga-/Cupdetail | Welche Regeln, Sichtbarkeit und Belohnung gelten hier? | melden, vorbereiten oder Verlauf ansehen |
| `VIS-01` | Titelübersicht | Welche Character-plus-Aspekt-Titel existieren? | Titelkontext öffnen |
| `VIS-02` | Challenger-Pool | Welche Bilder sind für diesen Titel qualifiziert? | Fortschritt und Kandidaten prüfen |
| `VIS-03` | 16er-Bracket | Wie verläuft dieser visuelle Wettbewerb? | nächstes Duell spielen |
| `VIS-04` | Finale oder Title Match | Wird diese Bildkarte Champion oder verbessert sie ihren Titel? | Vergleich entscheiden und Resultat ansehen |
| `EVO-01` | Kartenlaufbahn | Welche Kampferfahrung hat diese Karte gesammelt und steht eine Entwicklung an? | Ursprung, Formen und Schwelle prüfen |
| `EVO-02` | Evolution Trial | Wie soll die verdiente Entwicklung dieser Erinnerung als aktive Karte aussehen? | vier Kandidaten bewerten oder bisherigen Stand bewahren |
| `EVO-03` | Evolutionsenthüllung | Welche neue aktive Form hat die Karte angenommen? | neue Form und unveränderten Ursprung vergleichen |
| `BAT-01` | Battle-Home | Welche PvE-Herausforderung ist jetzt relevant? | Gegner oder Event wählen |
| `BAT-02` | Gegner-/Eventdetail | Warum spiele ich dieses Match und was steht auf dem Spiel? | Match vorbereiten |
| `BAT-03` | Matchvorbereitung | Welches Deck und welche Bedingungen gelten? | gültiges Deck bestätigen |
| `BAT-04` | Starthand | Mit welchem Plan beginne ich? | erlaubten Mulligan abschließen |
| `BAT-05` | Spielfeld | Welche Kartenaktion ist jetzt möglich und warum? | Karte spielen, angreifen oder Phase beenden |
| `BAT-06` | Kampfergebnis | Was hat sich durch Sieg oder Niederlage verändert? | Story-, Reward- oder Rückweg wählen |

Booster, Visual Circuit und Card Battler besitzen sichtbar verschiedene
Inszenierungen. Der Visual Circuit vergleicht Bildkandidaten und vergibt
Character-plus-Aspekt-Titel. Der Card Battler ist ein regelhaftes PvE-Spiel mit
Decks, Effekten und Gegnern. Beide dürfen niemals unter dem unspezifischen Wort
`Cup` zusammenfallen.

`CARD-02` liegt bei einer neuen oder entwickelten Bildkarte zwischen dem
unmittelbaren Ergebnis `BST-03` und der finalisierten Enthüllung `BST-04`.
CardIdentity, Rules, Branding und Availability sind zu diesem Zeitpunkt bereits
serverseitig materialisiert. Der Screen schreibt ausschließlich einen
resumefähigen CardArtCompositionDraft und bei Bestätigung eine
presentation-only Revision; er erzeugt keine Bewertungsevidence und keine
VN-AssetSourceSelection. Bildlose Standardkarten überspringen diesen Screen.
Bis zur Bestätigung zeigt die Karte eine neutrale ausstehende Projektion statt
eines unbestätigten Kartengesichts.

Die Ligaoberfläche bildet ein einziges Wettbewerbssystem für gemischte Decks
ab; Standard-, Public- und persönliche Karten erhalten keine getrennten
Ligen. Die Evolutionsscreens zeigen Ursprungsmemory und aktive Kartenform
gleichzeitig. Sie dürfen eine angenommene Evolution weder als austauschbaren
Skin noch als Überschreiben des ursprünglichen Moments darstellen. Vier
Rejects lassen die bisherige Form unverändert und halten den Schritt für einen
späteren Versuch offen.

Karten-Home, Sammlung, Deckbau und Matchvorbereitung projizieren außerdem die
Quellenklasse `Standard | öffentliche Eventedition | persönliche Postkarte`.
Bei minderjährigen Accounts werden persönliche Booster und Karten nicht nur
ausgeblendet, sondern serverseitig als nicht zulässige Quelle erklärt;
Standard- und öffentliche Eventkarten halten den Battler vollständig
zugänglich. Bei Academy-Figuren ist die Altersvoraussetzung bereits durch den
volljährigen Eintritt erfüllt, die konkrete Einwilligung bleibt trotzdem
sichtbar eigenständig.

Persönliche NPC-Karten dürfen in diesen Screens nur erscheinen, wenn ihr Pack
Opening zuvor öffentlich oder gezielt für den Protagonisten sichtbar war. Das
Stream-Erlebnis darf deshalb begrenztes Kartenwissen erzeugen, aber weder den
privaten Quellmoment vollständig offenlegen noch den NPC-Draft als Entscheidung
des Protagonisten darstellen. Nicht gestreamte Gegnerkarten bleiben bildlos
beziehungsweise werden durch öffentliche Editionen ersetzt, bis eine zulässige
Freigabeinszenierung stattgefunden hat.

`BAT-05` kombiniert eine Phaser-basierte Spielfläche mit DOM-basierten
Kartentexten, Auswahl- und Reaktionsdialogen, Phase, Pause und Recovery. Phaser
stellt ausschließlich serverseitig bestätigte Matchprojektionen dar. Ein
optionales Reaktionsfenster ohne legale Spielerreaktion wird automatisch
gepasst und erzeugt keinen leeren Pflichtdialog. Der Runtimevertrag steht in
[`card-battler-runtime-architecture.md`](card-battler-runtime-architecture.md).

### Welt, Tagesablauf und VN

| ID | Screen | Primäre Spielerfrage | Hauptaktion |
|---|---|---|---|
| `LOC-01` | aktueller Orts-Hub | Wo bin ich, wann ist es und was kann ich hier tun? | lokale Aktion, Network, Planer oder Reise öffnen |
| `VN-01` | VN-Szene | Was geschieht und wie antworte beziehungsweise handle ich? | Dialog fortsetzen oder Choice treffen |
| `DAY-01` | Tagesplan | Wie nutze ich die verfügbaren Zeitabschnitte? | Aktivität in erreichbaren Slot legen oder bestätigen |
| `CAL-01` | Kalender | Was steht an und welche Folgen sind bereits bekannt? | Tag, Termin oder Event öffnen |
| `MAP-01` | abstrakte Ortsübersicht | Welche bekannten Orte sind jetzt erreichbar? | Ort auswählen |
| `MAP-02` | Orts-/Reisedetail | Was kostet die Reise und was ist dort möglich? | reisen oder zurückkehren |
| `ACT-01` | lokale Aktivitäten | Was kann ich hier mit Bezug zu einer Figur unabhängig von einer VN-Szene tun? | gültige Routine, Lern-, Freizeit- oder Battler-Aktivität ausführen |
| `CHR-01` | privates Figurenwissen | Was weiß meine Spielfigur tatsächlich über diese Person? | bekannte Beziehung, Memories und offene Anlässe prüfen |
| `JRN-01` | Chronicle | Was ist geschehen und welche nachvollziehbaren Fäden sind offen? | Eintrag oder bekannten Zusammenhang öffnen |

Die Ortsübersicht benötigt keine geografische Weltkarte und ist keine frei
scrollende Open-World-Karte. Sie darf als Liste, Hub-Graph oder andere
abstrakte Projektion erscheinen und zeigt nur bekannte, erreichbare und aktuell
fachlich erlaubte Orte. Der Tagesplan ist ebenso wenig
eine reine Kalenderdatenbank: Er erklärt Zeitkosten, Ortsbindung,
Voraussetzungen und die unmittelbar erkennbare Wirkung einer Auswahl.

### System- und Metaflächen

| ID | Screen | Zweck |
|---|---|---|
| `SYS-01` | Pause, Save, Load und Runverwaltung | Spielzustand sicher verlassen, fortsetzen oder wechseln |
| `SYS-02` | Settings, Content, Accessibility und Dienste | globale Präferenzen und explizite Freigaben verwalten |
| `ADV-01` | Advanced und Diagnose | technische Projektion, Providerzustand und Evidence für Entwicklung und Support |

`ADV-01` ist kein Teil der normalen Spielerführung. Er darf Rohbegriffe und
vollständige Provenienz zeigen, solange er eindeutig als technische Oberfläche
gekennzeichnet bleibt und keine zweite Spielautorität erzeugt.

## Vier getrennte Sichten auf dieselbe Figur

Die Figureninformation wird nicht in einen überladenen Universal-Screen
gepresst:

| Sicht | Enthält | Enthält ausdrücklich nicht |
|---|---|---|
| öffentliches Network-Profil | selbst veröffentlichte Angaben, sichtbare Posts, öffentliche Verbindungen | geheime Personality-Werte, unbekannte Memories, versteckte Storygates |
| privates Figurenwissen | nur durch die Spielfigur bekanntes Wissen, Beziehung, gemeinsame Ereignisse | globale Backend-Wahrheit und unveröffentlichte Posts |
| Character-Kartenportfolio | eigene Spiel-/Bildkarten, Titel, Visual-Circuit-Fortschritt und sichtbare Lücken | vollständige Beziehungssimulation und fremde versteckte Karten |
| Battler-Profil | öffentliche Matchdaten, Deckidentität soweit erlaubt, Rang und Events | private Chats, geheime Storyentscheidungen und technische Bild-Evidence |

Die vier Sichten dürfen einander verlinken, wenn der Zielkontext bekannt und
erlaubt ist. Sie bleiben dennoch distinct, damit der Spieler jederzeit erkennt,
ob er eine öffentliche Person, eine private Beziehung, ein Kartenportfolio oder
einen Wettbewerber betrachtet.

## Booster-zu-Karte-Flow im Ziel-Frontend

Ein regulärer Battle-Booster folgt später diesem verständlichen Ablauf:

```text
Post, Event oder Reward
→ Booster-Herkunft und Kartenmotiv
→ vier Kartenkörper öffnen
→ passende Trial-Runtime für die vier Bilder
→ unmittelbare vier Resultate
→ Sammlung und Visual Circuit
```

Das unmittelbare Ergebnis darf nicht auf ein LLM warten. Regeln,
CardIdentity, Reject/Keep/Favorite, Bildbindung und Eligibility werden
deterministisch serverseitig materialisiert. Eine noch ausstehende lokalisierte
Beschreibung oder Flavor-Copy verwendet einen klaren Fallback und kann später
über `NET-05` als finalisierte Kartenenthüllung zurückkehren. Das LLM benennt
und beschreibt, bestimmt aber weder Regeln noch Championstatus.

Ein Adult-Booster kann später als eigener, explizit freigeschalteter Bereich des
Networks existieren. Er nutzt eine deutlich andere Gestaltung und darf
Bildspiele sowie Bild-Evidence erzeugen, aber keine CardIdentity, Deckkarte,
Visual-Circuit-Eligibility oder Card-Battler-Belohnung.

## Verbindlicher M6-Screenumfang

M6 darf sich der späteren Network-/Kartenästhetik bedienen, bleibt funktional
aber ein Beweis des Lernloops. Der minimale, praktisch spielbare Umfang ist:

| ID | M6-Screen | Muss verständlich machen |
|---|---|---|
| `M6-01` | Loop-/Character-Übersicht | aktive Testfigur, aktueller Zyklus, verfügbare Aufgabe und nächste Hauptaktion |
| `M6-02` | Trial-Briefing | fokussiertes Motiv, sichtbare Bewertungsfrage, was gleich bleibt und was variiert |
| `M6-03` | Trial-Runtime | genau ein Bild- oder Vergleichsfokus und genau die dazugehörige Eingabe |
| `M6-04` | Trial-Resultat | gespeicherte Spielerentscheidung, verständlicher Effekt und nächster Schritt |
| `M6-05` | Supply-/Generierungszustand | ob ausgewertet, geplant, generiert, auf Worker gewartet oder konkret blockiert wird |
| `M6-06` | visueller 16er-Cup | Bracket, aktuelles Duell, Gewinner und Character-plus-Aspekt-Titel |
| `M6-07` | Zyklusvergleich | nachvollziehbarer Unterschied zwischen vorherigem und neuem Generierungszyklus und erneuter Einstieg in den Loop |

Qualifier, Ranking, Arena und Ten-Point Calibration benötigen innerhalb
`M6-03` jeweils einen eigenen Interaktionsvertrag. Ein gemeinsames Styling macht
sie nicht zu derselben Bedienoberfläche. Auf 4K darf das relevante Bild nicht
von weit entfernten Formularen getrennt werden; auf Tablet und 720p stehen Bild,
Frage und Eingabe in einer klaren Fokusfolge ohne dauerhaft konkurrierende
Panels.

Für die Abnahme sind Tablet-Portrait und Tablet-Landscape eigenständige
Layoutzustände. Portrait hält das unveränderte Fokusbild oben und die aktive
Bedienstufe darunter; Landscape darf eine koordinierte Zwei-Spalten-Bühne
verwenden. Kein Sticky- oder Fixed-Footer darf Reason-Flächen oder Touchziele
überlagern. Auf 4K bleibt die gesamte Trial-Bühne begrenzt, während die
Display-Schrift ausschließlich Überschriften und kurze Modusmarker prägt.
Fragen, Gründe und Aktionen verwenden eine normal gesetzte Leseschrift statt
flächigem Versalsatz.

M6 erzeugt keine fingierten Feedposts, Chats, Orte, Beziehungseffekte, Decks
oder Battles. Ein direkter `Trials`-Katalog ist in diesem Schnitt ein
Proof-/Entwicklungszugang. Im späteren Zielspiel öffnet dieselbe Runtime aus
Booster, Visual Circuit oder einem ausdrücklich freien Trainingsanlass und
kehrt in diesen Kontext zurück.

M6 erzeugt ebenso keine freigestellten oder normalisierten VN-Assets. Keep,
Favorite und Champion bleiben sichtbare Zustände des bewerteten Quellbilds;
`AssetSourceSelection`, Asset-Processing, Sprite-/Alpha-QA, Expression-Familien
und Place-Assets erscheinen erst in den dafür vorgesehenen post-M6-Slices.

## Game-UI- und Responsive-Regeln

- Jeder Screen besitzt eine dominante Spielerfrage und eine primäre Aktion.
- Der aktuelle Bild-, Karten-, Orts- oder Dialogfokus bleibt visuell größer und
  näher an seiner Eingabe als Status-, Diagnose- oder Erklärtext.
- Eine primäre und höchstens eine kleine sekundäre HUD-Gruppe dürfen den
  Spielraum dauerhaft rahmen; weitere Informationen liegen in Drawern oder
  eigenen Screens.
- Mobile, Tablet Portrait, Tablet Landscape, 720p, 1080p und 4K werden als
  eigenständige Layoutzustände geprüft. Skalierung allein ist kein responsives
  Konzept. Die 4K-Trial-Bühne bleibt höchstens 2400 px breit; Fokusbild und
  aktive Eingabe liegen immer innerhalb dieser gemeinsamen Bühne.
- Touchziele, Tastaturfokus, Browser-Back, Reload und Reduced Motion gehören zum
  Screenvertrag.
- Übergangsanimationen dürfen Booster und Karten wertig inszenieren, aber nie
  die nächste erforderliche Aktion oder einen fachlichen Blocker verdecken.

## Noch offen, ohne die Screen Map zu blockieren

- endgültiger Name und visuelle Marke des Networks,
- genaue Länge und authored Handlung des Network-only-Prologs,
- vollständiger Home-Bundle-Vertrag einschließlich Tageszeitvarianten,
- finale visuelle Marke, FX-, Audio- und Animationstuning des Card Battlers;
  Regeln, Ressourcen, Runtime- und Phaser-/DOM-Grenze sind in v0.1 entschieden,
- endgültige Eigennamen für Visual Circuit, Titel und Battler-Wettbewerbe,
- genaue Produktreihenfolge der post-M6-Slices innerhalb der bestehenden
  Roadmap.

Diese offenen Punkte ändern nicht die festgehaltene Hierarchie: VN als
Gesamtspiel, assetfähiger aktueller Ort als späterer Zwischen-Szenen-Hauptscreen,
Network als anfängliche Vollbild- und dauerhafte Geräteoberfläche sowie der Card
Battler als Network-Feature.
