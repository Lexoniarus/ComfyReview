# Abgleich der früheren Entscheidungs- und POC-Register

**Dokumentklasse:** `GOVERNANCE` · **Rolle:** Herkunfts- und
Geltungsabgleich, **kein zweites aktives Entscheidungsregister**.  
**Ursprünglicher Registerabgleich:** 2026-10-09 · **Fachliche Einordnung aktualisiert:** 2026-10-10 · **Code-/Produktbasis:** ComfyReview, aus dem
Character Chronicles POC-getrieben hervorgehen soll.

## Herkunft und Leseregel

Am 9. Oktober wurden zwei Dokumente versehentlich auf
`refactor/review-boundary` statt auf den Dokumentations-PR geschrieben:

- [Früheres Entscheidungsregister: `docs/DECISIONS.md`](https://github.com/Lexoniarus/ComfyReview/blob/aa44f6ab39627e2fb922334db5ce8a2be3b7a3e1/docs/DECISIONS.md)
- [Früheres POC-Register: `docs/POC_REGISTER.md`](https://github.com/Lexoniarus/ComfyReview/blob/aa44f6ab39627e2fb922334db5ce8a2be3b7a3e1/docs/POC_REGISTER.md)

Diese Dateien wurden anschließend auf dem Basisbranch zurückgenommen. Die
folgenden **Quell-IDs** bewahren ihre Herkunft, schaffen aber **keine neu
genehmigten Beschlüsse, fest reservierten Arbeitspakete oder global gültigen
IDs**. Bei einem Widerspruch ist die rechts genannte aktuelle Fachstelle
maßgeblich. **Ein früher als `ACTIVE` bezeichneter Eintrag bleibt nicht
automatisch `DECIDED_FOR_SCOPE`.**

**Zuständigkeit:** [Bestätigte Rahmenbedingungen](CONFIRMED_CONSTRAINTS.md)
für tatsächlich bestätigte Vorgaben;
[Projektentwicklung](PROJECT_EVOLUTION.md) für die ungefähre Richtung;
[Decision Policy](DECISION_POLICY.md) für Entscheidungsregeln;
[Offene Entscheidungen](OPEN_DECISIONS.md) für ungelöste Fragen;
[aktiver Card-Battler-POC](pocs/card-battler.md) für den vereinbarten
ersten Versuch; [Vision](character-chronicles/vision/README.md) für
längerfristige fachliche Ideen. Historische Texte unter
[`sources/`](character-chronicles/sources/README.md) haben
keine normative Wirkung.

## Einzelzuordnung der früheren CRCC-Aussagen

| Quell-ID | Frühere Aussage | Aktuelle Einordnung und Geltung | Maßgeblicher Ort |
| --- | --- | --- | --- |
| `CRCC-001` | ComfyReview soll sich zur Character-Chronicles-Produktrichtung entwickeln, kein automatischer Repo-Split | **Bestätigte Produktrichtung im Scope dieser Entwicklung**; keine Entscheidung, dass jedes heutige Modul, Schema oder Frontend erhalten bleiben muss | [Bestätigte Rahmenbedingungen](CONFIRMED_CONSTRAINTS.md), [Projektentwicklung](PROJECT_EVOLUTION.md) |
| `CRCC-002` | Card Battler → Timeline → Social/Chat → Storyline → VN | **WORKING_DIRECTION**, grobe veränderbare Priorität, weder starre Phasen noch automatisch genehmigter MVP | [Projektentwicklung](PROJECT_EVOLUTION.md), [Zielbild](character-chronicles/vision/README.md) |
| `CRCC-003` | Frühere Chronicle-Implementierung und ihre Vertragsautorität verworfen | **SUPERSEDED/REJECTED nur für die alte technische Architektur**; Erzähl- und Spielideen dürfen als historische Quellen geprüft werden | [Historischer Code-Audit](character-chronicles/HISTORICAL_CODE_AUDIT.md), [Decision Policy](DECISION_POLICY.md) |
| `CRCC-004` | POC-Ergebnisse gehen einer neuen Implementierungsentscheidung voraus | **Bestätigter Arbeits-/Entscheidungsgrundsatz für den aktuellen Scope**; kein POC nimmt seine eigene Produktionsfreigabe vorweg | [Decision Policy](DECISION_POLICY.md), [POC-Index](pocs/README.md) |
| `CRCC-005` | Eigentliche VN-Content-Entwicklung zuletzt | **WORKING_DIRECTION**; kleine frühere Feasibility-POCs zu Freistellung, Matting, Schnittstellen und Komposition bleiben möglich | [Projektentwicklung](PROJECT_EVOLUTION.md), [VN-Zielbild](character-chronicles/vision/visual-novel.md) |
| `CRCC-006` | Alter ComfyReview-Card-Battler-Zielvertrag sei für „Phase 1“ aktiv genehmigt | **Als automatische Genehmigung nicht übernommen**: Das [frühere Plandokument](archive/card-battler-target-2026-10-02.md) bleibt `HISTORICAL_CLAIM`/Ideenquelle. **IN_PROGRESS** ist nur der getrennt benannte aktuelle Karten-POC; Match-, Deck-, CB-1-bis-CB-7- und Persistenzvorgaben bleiben zu prüfen | [Card-Battler-POC](pocs/card-battler.md), [Offene Entscheidungen](OPEN_DECISIONS.md) |

Die ungefähre technische Produktausrichtung ist mit den Quellen kompatibel.
**Der Weltkern ist inzwischen bestätigt**: Kobe/Japan ab 2032,
zwei Academy-Jahre für Erwachsene, die bestehende Social-/Battler-Kultur
und eine langfristig VN-/beziehungsorientierte Geschichte.
**Academy/Schuljahr ist in der Welt verbindliches Ziel**, aber
**keine sechste technische Pflichtphase**.
[Zielwelt](character-chronicles/vision/world.md). Weder die früheren `CRCC-`-IDs noch die
früheren Card-Battler-`CB-`-Slices werden automatisch zu neuen
Implementierungs-Gates.

## Einzelzuordnung der früheren POC-Vorschläge

Die folgenden `POC-00x`-Kennungen stammen **ausschließlich aus dem
zurückgenommenen Vorschlagsregister**. Sie sind keine neu gestarteten
Projekte. Das aktive POC-Ziel für die erste Karte ist separat unter
[Card Battler](pocs/card-battler.md#konkreter-erstversuch-eine-karte-von-der-bildwahl-bis-zur-sammlung)
beschrieben.

| Quell-ID | Frühere Prüffrage | Aktueller Status / Abgrenzung | Maßgeblicher Ort |
| --- | --- | --- | --- |
| `POC-001` | Deterministischen spielbaren Matchkern samt Deckrevisionen und Replay prüfen | **CANDIDATE** für spätere Match-/Deckintegration, **nicht** die bereits laufende erste Kartenerstellung und noch kein nachgewiesenes PvE-Spiel | [Card-Battler-POC](pocs/card-battler.md), [Offene Entscheidungen](OPEN_DECISIONS.md) |
| `POC-002` | Kartenkunst-, Darstellungs- und Renderingpipeline prüfen | **CANDIDATE** für technische Pipeline/UX. Der **ComfyReview-Entwicklungs-POC** erlaubt vier Bildoptionen, Auswahl oder vollständiges Ablehnen und Neugenerieren. In **Character Chronicles** soll später eine der vier Varianten ausgewählt werden. Die POC-Verwerfung ist keine automatisch gültige Spielregel; kein Renderer oder fertiger Art-Workflow ist dadurch beschlossen | [Card-Battler-POC](pocs/card-battler.md), [Vision](character-chronicles/vision/card-battler.md) |
| `POC-003` | Bedeutung, Zustandsmodell und UI einer Timeline erproben | **CANDIDATE**; Minimalumfang und Akzeptanz noch offen, kein separater Pflichtrelease | [Timeline-Zielbild](character-chronicles/vision/timeline.md), [Offene Entscheidungen](OPEN_DECISIONS.md) |
| `POC-004` | Posts, Charakter-Chats, Zustände und Providergrenzen erproben | **CANDIDATE**; Social/Chat baut fachlich auf einem Timeline-Slice auf, technische Plattform offen | [Social-Network-Zielbild](character-chronicles/vision/social-network.md), [Offene Entscheidungen](OPEN_DECISIONS.md) |
| `POC-005` | Storyentscheidungen, Zustand und Rückwirkung erproben | **CANDIDATE** für die Umsetzung der **bestätigten zwei Academy-Jahre**; altes Campaign-Schema und alte DayInstance-Vorgaben sind keine Pflicht | [Storyline-Zielbild](character-chronicles/vision/storyline.md), [Offene Entscheidungen](OPEN_DECISIONS.md) |
| `POC-006` | VN-Asset-/Content-Ausspielpipeline erproben | **CANDIDATE für den späteren Content-Ausbau**; kleine vorgelagerte technische Machbarkeitsversuche bleiben möglich | [VN-Zielbild](character-chronicles/vision/visual-novel.md) |

## Was aus der früheren Fassung nicht still übernommen wird

- Die früheren Kennzeichnungen `ACTIVE`, `APPROVED_TARGET` oder
  `CANDIDATE` sind **Quellenbehauptungen**, keine automatische neue
  Freigabe oder ein neues Pflichtregister.
- Ein Match-Replay-/Serverautoritäts-POC ersetzt **nicht** den
  [vereinbarten Spielerablauf der Kartenerzeugung](pocs/card-battler.md).
- Die früheren `CB-1` bis `CB-7` des großen Card-Battler-Plans sind
  **keine** verbindliche Implementierungsreihenfolge.
- Die noch offenen **Detailfragen** (Spielregeln, Deckgröße, Storydaten,
  Timeline-/Chat-Verhalten, KI-Provider, VN-Asset-Pipeline) werden erst
  anhand neuer POCs und ausdrücklich begrenzter Entscheidungen festgelegt.

**Regel für spätere Änderungen:** Den tatsächlichen Befund am Code/POC
feststellen, die fachlich verantwortliche aktuelle Datei aktualisieren
und eine neue ausdrücklich bestätigte Entscheidung nur in deren konkretem
Scope dokumentieren. Dieses Herkunftsdokument nicht als zweiten
Anforderungs- oder Meilensteinplan fortschreiben.
