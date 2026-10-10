# Character Chronicles – eigenständiger Game-Client

**Stand:** CC-GAME-02, 2026-10-10 · **Arbeitsbranch:**
`feature/character-chronicles-game-client` · **Editor:** Cocos Creator 3.8.8

## Was hier tatsächlich existiert

`cocos/` ist ein **echtes, mit Cocos Creator 3.8.8 erzeugtes Projekt**.
Die vorhandene Editor-Szene `assets/GameShellController.scene` enthält
`Canvas`, `RoomRoot`, `OpenPhoneButton`, `PhoneOverlay` und einen mit diesen
Nodes verbundenen `GameShellController`.

CC-GAME-02 ergänzt eine **vorläufige, code-erzeugte Game-Shell**:

- Ein sichtbarer, schematisch gezeichneter Raum-Hub und der bereits in der
  Editor-Szene vorhandene Smartphone-Button.
- Ein überlagerndes Smartphone mit **Schließen**, **Timeline**,
  **Nachrichten** und **Karten**. Der Controller erzeugt die fehlenden
  UI-Nodes und Button-Handler beim Laden der Szene.
- Ausdrücklich gekennzeichnete Demo-Posts, Demo-Nachrichten und Demo-Karten.
  Sie sind statisch und werden **nicht** durch Backend-Spielzustand gespeist.
- Reine, headless testbare Navigation in `GameShellState.ts`. Schließen des
  Telefons merkt sich den zuletzt geöffneten Tab; es gibt keine Server-Mutation.
- Optional bleibt die vorhandene `CanonicalImagePreview`-Komponente verfügbar,
  falls der Projektbesitzer später für einen separaten API-Smoke ein echtes
  `image_uid` samt Inspector-Verknüpfung einträgt. Für CC-GAME-02 ist **kein**
  API-Server erforderlich.

**Wichtig:** TypeScript und Headless-Tests sind geprüft; der tatsächliche
Import, die Darstellung, Klick-Hitboxes und das Laufzeitverhalten im Cocos
Editor **müssen vom Projektbesitzer noch getestet und abgenommen werden**.
Der Cocos-Editor war für diesen Arbeitsschritt nicht verfügbar.

## Schnellstart auf dem lokalen Rechner

1. Die vorhandene Branch `feature/character-chronicles-game-client` in Git
   aktualisieren. Das Projekt **nicht noch einmal neu erzeugen** und den
   Installer nicht über die vorhandenen Dateien laufen lassen.
2. Cocos Creator **3.8.8** öffnen und
   `game-client/cocos` als bestehendes Projekt öffnen.
3. Im Assets-Bereich `GameShellController.scene` öffnen; warten, bis
   Cocos alle TypeScript-Dateien importiert hat. Für die neue
   `GameShellView.ts` erzeugt **der Editor** die zugehörige `.meta`-Datei.
4. **Preview / Play** starten. Den Smartphone-Button, die drei Tabs,
   Schließen und erneutes Öffnen testen.
5. Falls ein **Web-Desktop-Build** statt Preview gewünscht ist: im Cocos
   Build-Fenster diese Szene als Startszene auswählen und den Build erzeugen.
   Eine vorherige Startszene-Konfiguration ist nicht verifiziert.

Die detaillierten Prüfpunkte stehen in [GAME_SHELL.md](GAME_SHELL.md).
Weiteres zur optionalen Bild-API und zum lokalen Web-Proxy:
[SETUP.md](SETUP.md).

## Architektur und Grenzen

Der **Python-/FastAPI-Core** bleibt allein für Spielregeln, Persistenz,
Bildgenerierung und die zukünftigen Social-/Card-/Story-Daten verantwortlich.
Die bestehende ComfyReview-Studiooberfläche in `templates/` und `static/`
bleibt unverändert. Der Game-Client ist eine Darstellungsschicht und
**keine zweite Fachlogik**.

CC-GAME-02 führt **keine** Social-, Chat-, Card-Battler-, Academy- oder VN-API
ein, keine Spielstanddatei, keinen lokalen KI-Aufruf, keine neue Datenbank und
**keine FairyGUI-Abhängigkeit**. Die Grafiken sind ausschließlich temporäre
Cocos-`Graphics`-Flächen und eingebaute Textlabels; keine Fremd- oder
endgültigen Academy-Assets. Die feste Character-Chronicles-Weltvision steht
unter [`docs/character-chronicles/vision/world.md`](../docs/character-chronicles/vision/world.md).

### Relevante Dateien

| Pfad | Verantwortung |
| --- | --- |
| `cocos/assets/GameShellController.scene` | Echte Editor-Szene; unverändert |
| `cocos/assets/scripts/GameShellController.ts` | Navigation und Verbindung zur Szene |
| `cocos/assets/scripts/GameShellView.ts` | Code-erzeugte temporäre Raum-/Telefon-UI |
| `cocos/assets/scripts/runtime/GameShellState.ts` | Reine Navigation, ohne Cocos-/HTTP-Abhängigkeit |
| `cocos/assets/scripts/runtime/ComfyReviewImageApi.ts` | Bereits vorhandener optionaler Read-only-Bild-API-Adapter |
| `starter/assets/scripts/` | Synchroner Starter-Spiegel; keine zweite Runtime |
| `tests/` | Headless-Tests für Navigation und vorhandene Hilfsmodule |

## Prüfkommandos außerhalb des Editors

Ab Repository-Wurzel:

```bash
node --experimental-strip-types --test game-client/tests/*test.mjs
tsc -p game-client/tsconfig.contract.json
python -m unittest discover -s game-client/tests -p 'test_*.py'
```

Die TypeScript-Vertragsprüfung umfasst die beiden **reinen Runtime-Module**
und deren Starter-Spiegel. Sie ersetzt keine Typprüfung gegen die echten
Cocos-3.8.8-Engine-Deklarationen oder einen Engine-Build. Die beiden
Python-Skripttests und der Bild-API-Test gehören zum bestehenden Stand und
bleiben unverändert.

Die zukünftige FairyGUI-Integration, Runtime-Image-Smoke, native Builds,
Animationen, Responsive-UI und echte Spielabläufe werden separat entschieden;
CC-GAME-03 beginnt **nicht** automatisch.
