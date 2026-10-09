# Kartenkunst-Komposition und Kartengesicht-Rendering

Dokumentrolle: autoritativer technischer Zielvertrag für die Darstellung von
Bildkarten und bildlosen Standardkarten

Autorität: verbindliche Grenze zwischen CardIdentity, Bildbranding,
Spielregeln, manueller Kartenkunst-Komposition und gerendertem Kartengesicht

Rules-Kompatibilität: `card_battler_rules_v0.1`

Status: **Baseline abgeschlossen; implementierbarer Dokumentvertrag**

Stand: 14. September 2026

## Zweck und Abgrenzung

Dieses Dokument definiert, wie ein bereits bestätigtes Keep-, Favorite-,
Champion-, Public-Edition- oder Evolutionbild sichtbar in ein Kartengesicht
eingepasst wird. Es schließt die technische Lücke zwischen der semantischen
Bildbindung einer Karte und ihrer Darstellung in Sammlung, Deck und Match.

Es verändert weder Card-Battler-Regeln noch Bildbewertung:

- `CardRulesRevision` besitzt ATK, DEF, Rarity, Level, Traits und Kosten.
- `ImageBrandingRevision` bindet CardIdentity, ImageIdentity, dargestellte
  Hauptfigur, Situation, MemoryOrigin und Disclosure-Kontext.
- `CardArtCompositionRevision` bindet ausschließlich Frame, Bildausschnitt,
  Zoom, Position und das daraus reproduzierbar gerenderte Kartengesicht.

Eine Kartenkunst-Komposition ist insbesondere keine `AssetSourceSelection`,
kein `DerivedAssetImage`, keine `AssetVersion` und keine VN-Spriteproduktion.
Sie schreibt keine PlayerPreferenceEvidence, keine Keep-/Favorite-Disposition,
keinen Championtitel, keine Eligibility und keinen CharacterVisualCanon.
Unklare oder fehlende Quellenberechtigung kann weder durch Ausschnitt noch
Framewahl geheilt werden.

## Drei unabhängige Revisionsketten

```text
CardIdentity
├─ CardRulesRevision
│  └─ ATK, DEF, Rarity, Level, TraitLineage und ausführbare Effekte
├─ ImageBrandingRevision
│  └─ ImageIdentity, konkrete Hauptfigur, Situation und Herkunft
└─ CardArtCompositionRevision
   └─ FrameTemplateRevision, normalisierter Transform und CardFaceAssetRevision
```

Eine Änderung an einer Kette mutiert keine andere Kette still mit:

- Level Up oder Traitentwicklung erzeugt eine neue `CardRulesRevision`; eine
  neue Komposition ist nur nötig, wenn auch die aktive Bildrevision wechselt.
- Pan, Zoom, Frameaustausch oder erneutes Rendering verändern keine Regeln und
  würfeln keine Traits neu.
- Bildlöschung beendet Branding und aktive Kartenkunst. Dieselbe CardIdentity
  fällt gemäß Rules v0.1 auf ihr ursprüngliches bildloses Standardprofil zurück.
- Ein laufendes Match behält seine eingefrorenen Rules-, Branding-,
  Composition- und Face-Asset-Revisionen unverändert.

## Spielerflow und Materialisierungsreihenfolge

Ein regulärer Vierer-Booster bleibt sofort wirksam. Nach Abschluss des
Bildspiels materialisiert der Server pro Slot zuerst CardIdentity, Disposition,
Branding, Rules und Availability. Weder LLM-Copy noch manuelle Komposition darf
diese unmittelbare Materialisierung verzögern.

Für jedes positive bildgebundene Resultat entsteht anschließend genau ein
deterministischer `CardArtCompositionDraft`:

1. Der Server bindet Quell-ImageIdentity und aktuelle Brandingrevision.
2. Ein versioniertes Frame-Manifest liefert Bildfenster, Text- und
   Statistikanker sowie die zulässigen Transformgrenzen.
3. Eine reproduzierbare Cover-Fit-Berechnung erzeugt den zentrierten
   Ausgangsvorschlag.
4. Der Spieler darf das Bild hinter dem unveränderten Frame verschieben, hinein-
   oder herauszoomen, zurücksetzen und per Tastatur feinjustieren.
5. `Bestätigen` materialisiert eine immutable
   `CardArtCompositionRevision` und genau ein zugehöriges Render-Receipt.

Vor der Bestätigung existiert die Karte vollständig und ist regelgültig. Eine
noch unbestätigte Bildkomposition wird jedoch nicht als finalisiertes
Kartengesicht ausgegeben. Sammlung, Deck und Battler zeigen bis dahin eine
eindeutig als ausstehend erkennbare neutrale Kartenprojektion mit den bereits
gültigen Kartendaten. Damit blockiert Gestaltung weder Boosterabschluss noch
Deckstruktur oder den bildlosen Battler-Prototyp.

Der Spielerflow liegt zwischen `BST-03` und `BST-04`:

```text
BST-03 unmittelbares Kartenresultat
→ CARD-02 Kartenbild gestalten und bestätigen
→ serverseitiger reproduzierbarer Render
→ BST-04 finalisierte Kartenenthüllung
```

Bei mehreren bildgebundenen Resultaten bildet `CARD-02` eine resumefähige
Queue. Ein Abbruch verliert keinen bestätigten Schritt und verändert keine
unbestätigte CardIdentity. Historische Entwicklungsbilder dürfen über einen
expliziten `development_import` denselben Vertrag verwenden; Import und
Komposition erzeugen keine M6-Proof-Evidence.

Bildlose Standardkarten besitzen keine ImageBrandingRevision und keinen
Kompositionsdraft. Sie verwenden direkt die revisionierte neutrale
Standarddarstellung. Die Kartenrückseite ist ein eigenes Template und niemals
eine aus einer Vorderseite abgeleitete Komposition.

## Frame-Manifest und Mock-Grenze

Jedes Frame ist eine immutable `CardFrameTemplateRevision` mit mindestens:

```text
frame_template_revision_id
template_key
template_role = front | back
asset_manifest_key
asset_checksum
status = mock_only | candidate | production
canvas_width
canvas_height
art_window_normalized
art_clip_mask_manifest_key?
title_anchor_normalized
trait_text_bounds_normalized
attack_anchor_normalized
defense_anchor_normalized
badge_anchors_normalized[]
minimum_source_width
minimum_source_height
render_profile_revision
```

`art_window_normalized` wird pro Template ausdrücklich gepflegt. Es darf nicht
zur Laufzeit aus transparenten Pixeln, Dateirändern oder ähnlich aussehenden
Frames erraten werden. Vorder- und Rückseiten dürfen unterschiedliche
Abmessungen und Seitenverhältnisse besitzen.

Die am 14. September 2026 vorgelegte Framefamilie ist ausschließlich
`mock_only`. Ihre Farbvarianten beweisen Layout und Rendering, legen aber weder
die endgültige Zuordnung zu Common, Uncommon, Rare, Super, Ultra oder Legendary
noch Produktionsauflösung, Materialstil oder Exportformat fest. Ein späterer
Produktionsframe ersetzt die Mockrevision über einen neuen Manifesteintrag; er
überschreibt keine historische Revision und ändert keine Kartenregel.

## Normalisierter Kompositionsvertrag

Der persistierte Transform ist unabhängig von Browsergröße und
Quellbildauflösung:

```text
source_image_identity
source_image_revision
frame_template_revision_id
focus_x = 0.0 .. 1.0
focus_y = 0.0 .. 1.0
zoom = 1.0 .. frame_policy.max_zoom
rotation_degrees = 0 in v0.1
composition_policy_revision
```

`zoom = 1.0` bezeichnet den kleinsten Cover-Fit, bei dem das gesamte
Frame-Bildfenster ohne transparente oder fehlende Quellfläche bedeckt ist.
Pan wird nach jedem Pointer-, Touch-, Tastatur- oder Resize-Ereignis gegen diese
Coverage-Grenze geklemmt. Freies Drehen, nichtuniformes Skalieren,
Perspektivverzerrung und destruktives Beschneiden des Quellbilds gehören nicht
zu v0.1.

Client und Server verwenden dieselbe versionierte Transformformel. Der Browser
liefert lediglich eine Vorschau; ausschließlich der Server bestätigt Transform,
Framebindung und Outputhash.

## Rendervertrag

Der Browser rendert die interaktive Vorschau mit DOM, CSS-Transform und Canvas
2D. Der Server erzeugt das autoritative Kartengesicht mit Pillow oder einem
funktional äquivalenten, versionierten Renderer:

1. Quellbild anhand der gebundenen ImageRevision laden und Hash prüfen.
2. Cover-Fit und normalisierten Transform anwenden.
3. Auf das explizite Bildfenster beziehungsweise die Clipmaske begrenzen.
4. Frameoverlay, bestätigte Textprojektion, Badges und ATK-/DEF-Werte in stabiler
   Z-Reihenfolge zusammensetzen.
5. Farbraum, Ausgabedimensionen und Encoding gemäß RenderProfile normalisieren.
6. Output speichern und `CardFaceRenderReceipt` mit allen Inputrevisionen,
   Rendererrevision und Outputhash schreiben.

`CardFaceAssetRevision` ist eine presentation-only Ableitung. Sie ist keine
neue ImageIdentity, keine Bildkarte und keine VN-AssetVersion. Ein Retry mit
identischen Inputs ist idempotent und muss denselben semantischen Renderkey
liefern. Eine technisch neue Encoderrevision darf einen neuen Binärhash
erzeugen, muss dann aber als eigene Rendererrevision nachvollziehbar bleiben.

## Fachliche Zuständigkeiten

| Modul | Verantwortung |
|---|---|
| `card_crafting` | Draft anlegen, Transform validieren, CompositionRevision bestätigen und Render autorisieren |
| `card_collection` | aktive/historische Composition- und Face-Asset-Revisionen sowie Pending-Status projizieren |
| `card_battler` | beim Matchstart die aktive presentation-only Revision einfrieren, aber nie Komposition berechnen |
| `web_ui` | DOM-Editor, Canvas-Vorschau, semantische Eingaben, Resume und Accessibility |
| `asset_processing` | keine Verantwortung; bleibt ausschließlich beim getrennten VN-Asset-Lifecycle |

## UI-, Input- und Accessibility-Vertrag

Der Editor zeigt genau eine dominante Aufgabe: den sichtbaren Bildausschnitt
der aktuellen Karte festlegen. Frame, Quellbild und Ergebnisvorschau bleiben
gemeinsam sichtbar; Kartentext darf in einem DOM-Drawer oder einer
Sekundärfläche gelesen werden.

Pflichtaktionen sind:

- Drag beziehungsweise Ein-Finger-Pan,
- Mausrad- und Pinch-Zoom,
- sichtbarer Zoom-Slider mit Zahlenwert,
- Pfeiltasten zur Feinverschiebung,
- `+`/`-` zum Zoomen,
- `Zurücksetzen`, `Abbrechen`, `Bestätigen`,
- verständlicher Fokuszustand und Screenreader-Name jeder Aktion.

Ein aktiver Editor besitzt die Pointer-/Touch-Eingabe vollständig; ein später
parallel sichtbares Phaser-Board darf darunter keine Eingabe erhalten. Reduced
Motion deaktiviert nichtfunktionale Übergänge, verändert aber weder Transform
noch Renderoutput. Auf kleinen Viewports bleibt die Karte vollständig
erreichbar; Bedienelemente dürfen das Bildfenster nicht überdecken.

## Bibliotheks- und Implementierungsbaseline

Für den ersten Spike gilt:

- `@panzoom/panzoom` ist die bevorzugte kleine UI-Abhängigkeit für Pointer-,
  Touch-, Pan- und Zoom-Gesten im frameworkfreien Vite-Frontend.
- Native Canvas 2D erzeugt die Vorschau und Frame-/Maskenkomposition.
- Das bereits verwendete Pillow erzeugt den autoritativen Backend-Render.
- Hypothesis prüft Normalisierungs-, Coverage-, Idempotenz- und
  Reducerinvarianten; Playwright prüft reale Pointer-, Touch-, Tastatur-,
  Reload- und Resume-Flows.
- Phaser wird ausschließlich für das spätere Battler-Board verwendet und ist
  keine Editorabhängigkeit.

Cropper.js bleibt eine Alternative für einen späteren frei wählbaren
Rechteckausschnitt. Konva oder Fabric.js werden erst neu bewertet, wenn ein
echter Mehrlayer-WYSIWYG-Editor mit frei beweglichen Texten, Badges oder
Objekten beschlossen wird. Diese Funktionen gehören nicht zum jetzigen Scope.

Unabhängig von der UI-Bibliothek bleiben Frame-Manifest, normalisierte
Transformformel, Coverage-Clamping, Persistenz, Servervalidierung, Rendering,
Receipts und Accessibility eigene Produktlogik.

## API-Vertrag

Die Ziel-API verwendet ausschließlich HTTP:

| Methode und Pfad | Verantwortung |
|---|---|
| `GET /api/vnext/card-collection/cards/{card_id}/art-composition` | Aktiven Draft, bestätigte Revision, Frame-Manifest, Preview-URL und erlaubte Aktionen lesen. |
| `POST /api/vnext/card-collection/cards/{card_id}/art-composition-drafts` | Idempotent einen Draft für die aktive Branding-/Bildrevision erzeugen oder fortsetzen. |
| `POST /api/vnext/card-collection/cards/{card_id}/art-composition-drafts/{draft_id}/commands` | `set_transform | reset_transform | confirm | cancel` mit `command_id` und `expected_revision` ausführen. |

`set_transform` trägt normalisierte Werte und niemals browserabhängige
Pixelkoordinaten. `confirm` ist nur zulässig, wenn Branding, ImageRevision,
FrameRevision und Draftrevision noch aktuell und die Coverage-Invarianten
erfüllt sind. Ein stale Command liefert HTTP 409 mit der aktuellen
viewergefilterten Projektion und verändert nichts.

## Persistenz und Recovery

Die Zielpersistenz umfasst:

- `card_frame_template_revisions`,
- `card_art_composition_drafts`,
- `card_art_composition_draft_events`,
- `card_art_composition_revisions`,
- `card_face_asset_revisions`,
- `card_face_render_receipts`.

Bestätigte Revisionen und Render-Receipts sind append-only. Ein Draft besitzt
eine monotone Revision und darf resumiert, verworfen oder nach geänderter
Branding-/Framebasis als stale markiert, aber nicht still auf neue Inputs
umgebunden werden. Temporäre Previewdateien sind rebuildbar und keine
Autorität.

Nach einem Crash zeigt `GET .../art-composition` entweder den letzten
bestätigten Draftzustand, die bereits atomar bestätigte CompositionRevision
oder einen recoverbaren Renderfehler. Ein überschrittenes technisches
Renderbudget erzeugt keine Spielerentscheidung und keine Kartenmutation.

## Testbare Invarianten und Abnahme

1. Gleiche Source-, Frame-, Transform-, Text- und Rendererrevision erzeugt
   denselben semantischen Renderkey.
2. Kein zulässiger Transform lässt das Frame-Bildfenster unbedeckt.
3. Vorschau und Serverrender zeigen innerhalb der definierten Pixeltoleranz
   denselben Bildausschnitt.
4. Wiederholte Commands erzeugen keine zweite bestätigte Revision oder
   doppeltes Render-Receipt.
5. Stale Drafts können weder neue Branding- noch FrameRevisionen überschreiben.
6. Pan, Zoom, Reset und Bestätigung verändern weder CardRulesRevision noch
   Review-, Champion-, Eligibility- oder VN-Assetzustand.
7. Eine bildlose Standardkarte ist ohne Kompositionsrecord spiel- und
   renderfähig.
8. Ein laufender Matchsnapshot bleibt nach neuer Komposition, Frameaustausch
   oder Bildlöschung visuell und regeltechnisch unverändert.
9. Historischer `development_import` erzeugt keine M6-Proof-Evidence.
10. Maus, Touch, Tastatur, Reload, Reduced Motion und kleine Viewports besitzen
    einen vollständigen, nicht blockierenden Pfad.

## Bewusst spätere Kalibrierung

Keine offene Produktentscheidung sind die genaue Produktionsauflösung,
Kompressionsparameter, Mindestquellauflösung, finale Clipmasken und die
ästhetische Zuordnung konkreter Framefamilien zu Rarity-Stufen. Sie werden mit
echten Produktionsframes kalibriert und über neue Manifest- beziehungsweise
RenderProfileRevisionen eingeführt. Die Identitäts-, Autoritäts-, Lifecycle-
und Snapshotgrenzen dieses Dokuments bleiben dabei unverändert.
