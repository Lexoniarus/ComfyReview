# CC-GAME-02 – spielbare Raum- und Smartphone-Shell (POC)

**Stand:** Code erstellt, headless überprüfbar, echter Cocos-Editor-Test und
Abnahme durch den Projektbesitzer stehen aus. Kein fertiges Spielsystem.

## Was beim Szenenstart passiert

Die **bereits im Cocos Creator 3.8.8-Editor gespeicherte** Szene
`game-client/cocos/assets/GameShellController.scene` wird geöffnet. Sie
enthält die originalen Nodes `Canvas`, `GameShell`, `RoomRoot`,
`OpenPhoneButton` und `PhoneOverlay`. `GameShellController.onLoad()` nutzt
die vorhandenen Inspector-Verweise und ruft den neuen `GameShellViewBuilder`
auf. Dieser erzeugt mit Cocos `UITransform`, `Graphics`, `Label` und `Button`
vorläufige sichtbare Elemente **im laufenden Spiel**, keine neue Scene-Datei.

Der Raum zeigt eine schematische Wand/Bodenfläche, ein Fenster, Schreibtisch,
Regal und den bereits editorseitig vorhandenen Button **Smartphone öffnen**.
`RoomRoot` bleibt hinter dem Telefon sichtbar. Die Darstellung ist reiner
Platzhalter, ohne finale Academy-Assets oder fremde Bilddateien.

## Smartphone-Navigation

| Aktion | UI-Verhalten | Spiel-/Backendwirkung |
| --- | --- | --- |
| Smartphone öffnen | Telefon über dem Raum; zunächst Timeline | Keine |
| Timeline | Demo-Posts sichtbar; andere Tabs verborgen | Keine |
| Nachrichten | Demo-Nachrichten sichtbar; andere Tabs verborgen | Keine |
| Karten | Drei Demo-Karten sichtbar; andere Tabs verborgen | Keine |
| X / Schließen | Telefon verborgen; Raum bleibt erhalten | Keine |
| Erneut öffnen | Zuletzt besuchter Tab sichtbar | Keine |

Der bestehende `OpenPhoneButton` behält sein **im Editor gespeichertes**
Click Event `GameShellController.openPhone`. Schließen und die drei Tabs
werden durch den Builder erzeugt und mit `Button.EventType.CLICK`
verbunden. Der gesamte Telefonbereich blockiert Eingaben an darunter
liegenden Room-Nodes.

Die Logik `GameShellState.ts` hält nur `screen` und `phoneTab`; es gibt
weder Persistenz noch API-Aufrufe. Jede Beispielansicht ist mit **DEMO**
markiert. Beim Tabwechsel gibt es keine fachlichen Mutationen. Der separate,
optionale vorhandene kanonische Bild-Preview wird **nur** angesprochen,
wenn ein echtes `image_uid` **und** eine Preview-Komponente im Inspector
vorhanden sind. Diese UI benötigt beides nicht.

## Entwicklungsaufteilung

- `cocos/assets/scripts/GameShellController.ts` – Editor-Szene verbinden,
  Navigation rendern, optionalen Bild-Preview steuern.
- `cocos/assets/scripts/GameShellView.ts` – sichtbare provisorische
  UI-Flächen und Buttons aufbauen; hier später den Platzhalter ersetzen.
- `cocos/assets/scripts/runtime/GameShellState.ts` – pure Navigation
  (wiederholtes Öffnen/Schließen, genau ein aktiver Tab).
- `starter/assets/scripts/` – unverändertes API-Modul und synchroner Spiegel
  der hier geänderten TypeScript-Quellen.
- `.scene`/`.meta` – vom Cocos Editor verwaltet. CC-GAME-02 ändert sie nicht;
  die `.meta` für die neue TS-Datei wird beim nächsten Editor-Import erzeugt.

## Schnelle manuelle Abnahme in Cocos Creator 3.8.8

1. Repository-Branch aktualisieren und das **bestehende** Projekt
   `game-client/cocos` öffnen.
2. `assets/GameShellController.scene` öffnen, Skriptimport abschließen und
   Preview starten (für Web-Builds die Szene als Startszene auswählen).
3. Raum sichtbar? Button **Smartphone öffnen** anklicken: Telefon sichtbar?
4. Timeline / Nachrichten / Karten nacheinander anklicken: genau ein
   Demo-Panel sichtbar? Visueller Tabwechsel und Beschriftungen korrekt?
5. **X** klicken: Telefon weg, Raum sichtbar? Telefon mehrfach öffnen und
   schließen; zuletzt gewählter Tab bleibt erhalten?
6. Konsolenausgabe auf Engine-/Skriptfehler prüfen. Für Cocos-Import- oder
   Darstellungsprobleme die genaue Meldung/Screenshot für die Abnahme sichern.

Es müssen **keine neuen UI-Nodes oder Click Events** im Inspector angelegt
werden. Nur die zwei bereits gespeicherten `RoomRoot`-/`PhoneOverlay`-
Referenzen müssen weiterhin vorhanden sein.

## Nachweis und ausdrücklich offene Punkte

Headless-Tests testen die Navigation einschließlich Tab-Exklusivität,
Wiederholungszyklen und die Übereinstimmung von Editor- und Starterquellen.
`tsc -p game-client/tsconfig.contract.json` prüft die reinen Runtime-Module.
Tests **ohne** echtes Cocos SDK können nicht beweisen, dass importierte
Skripte, Klickflächen und Layout im Editor oder Web-Build funktionieren.

Ausstehend: realer Cocos Editor/Preview/Build, verschiedene Auflösungen,
Responsive-Layout, Bedienung per Touch/Tastatur, optionales Bildladen und
Texturlifecycle, Animationen, FairyGUI, persistierte Spielzustände und echte
Social-/Chat-/Card-Battler-Daten. Keine dieser Funktionen wird in CC-GAME-02
als bereits integriert bezeichnet. **Die finale manuelle Freigabe erfolgt
ausschließlich durch den Projektbesitzer.**

CC-GAME-03 wird erst nach gemeinsamer Sichtung dieses Commits beauftragt.
