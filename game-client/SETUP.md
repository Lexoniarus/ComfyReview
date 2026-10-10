# Character Chronicles – Cocos Creator 3.8.8 einrichten

**Stand CC-GAME-02:** Das Cocos-Projekt und die Startszene wurden bereits im
**echten Cocos Editor** angelegt und sind im Branch eingecheckt.
Ein erneutes Dashboard-„New Project“ ist **nicht erforderlich**.

## Bestehendes Projekt öffnen und die Shell testen

1. Branch `feature/character-chronicles-game-client` aktualisieren.
2. Cocos Creator **3.8.8** über Cocos Dashboard öffnen und das vorhandene
   Projekt im Ordner `game-client/cocos` auswählen.
3. In Assets die Szene `GameShellController.scene` doppelklicken.
4. Den TypeScript-Import abschließen lassen. Die neue Skriptdatei
   `GameShellView.ts` erhält ihre `.meta` **automatisch vom Editor**;
   weder die Szene noch deren `.meta` wurden manuell hergestellt/verändert.
5. Im Inspector von `GameShell` kontrollieren, dass die vorhandenen Felder
   `roomRoot → RoomRoot` und `phoneOverlay → PhoneOverlay` zugewiesen sind.
   Andere Nodes oder Click Events sind für CC-GAME-02 nicht manuell nötig.
6. Über **Preview / Play** starten, auf **Smartphone öffnen** klicken,
   zwischen **Timeline**, **Nachrichten** und **Karten** wechseln, mit **X**
   schließen und erneut öffnen. Jeder Tab zeigt ausdrücklich Demo-Inhalte.

Falls Preview keine Szene anzeigt, erneut `GameShellController.scene` öffnen
und im Editor die Konsole auf Import- oder Skriptfehler prüfen. Für einen
Web-Desktop-Build im Build-Fenster diese Szene als Startszene festlegen.
Der **Build und der echte Editor-Test sind noch ausstehend**.

## Keine manuelle Cocos-Metadaten-Erzeugung

`cocos/assets/GameShellController.scene` und ihre `.meta` sind authentische,
mit dem Editor erstellte Dateien. Der CC-GAME-02-Code ergänzt Nodes und
Event-Handler bei `onLoad()` im Speicher. Bestehende Editor-Nodes werden
beibehalten, insbesondere der ursprüngliche `OpenPhoneButton` samt
vorhandenem `openPhone`-Click-Event. Keine `.scene`-Datei wird gescriptet oder
außerhalb des Editors von Hand verändert.

`starter/` ist nur ein Spiegel der TypeScript-Quellen für eine eventuelle
**neue** Editorinstallation. Das Hilfsskript `scripts/install_starter.py`
verweigert das Überschreiben vorhandener geänderter Dateien. **Nicht**
über dem eingecheckten Cocos-Projekt ausführen; dort genügt `git pull`.

## Optional: Read-only-Smoke mit einem kanonischen Bild

Die Smartphone-Demo braucht **keinen laufenden FastAPI-Server**. Der bereits
vorhandene `CanonicalImagePreview` kann unabhängig davon ein echtes
`image_uid` über `GET /api/v2/images/{image_uid}` laden. Dazu in einer
separaten, durch den Editor erstellten Preview-Node die Komponente
`CanonicalImagePreview` und ein Sprite/Statuslabel verbinden, beim
`GameShellController` diese Node als `avatarPreviewNode` zuweisen und eine
sichtbare echte `demoAvatarImageUid` eintragen. Dieser Schritt ist optional
und für CC-GAME-02 **nicht als durchgeführt oder abgenommen** markiert.

Für Web-Builds gilt Same-Origin: Ein von einer fremden Origin geladener
ComfyReview-PNG-Pfad kann an Browser-CORS scheitern. Für einen lokalen,
**nur an 127.0.0.1 gebundenen** Bild-Test dient der vorhandene Proxy:

```powershell
python game-client/scripts/dev_proxy.py --build "game-client/cocos/build/<tatsaechlicher-web-build-ordner>"
```

Voraussetzung ist ein durch den Cocos-Editor erstellter Web-Desktop-Build mit
`index.html` und die lokal laufende FastAPI-Anwendung auf
`http://127.0.0.1:8000`. Danach `http://127.0.0.1:8787/` öffnen. Der Proxy
leitet ausschließlich `/api/v2/` und `/files/` weiter; er ist **kein**
öffentliches Deployment und kein Authentifizierungssystem. Keine Änderung
an FastAPI-CORS oder Browser-Sicherheit ist dafür nötig.

Native-Transport, Image-Lifecycle, Texturfreigabe und FairyGUI Community sind
separate, weiterhin nicht abgenommene Integrationsprüfungen.

## Headless-Checks (ohne Cocos-Editor)

```bash
node --experimental-strip-types --test game-client/tests/*test.mjs
tsc -p game-client/tsconfig.contract.json
python -m unittest discover -s game-client/tests -p 'test_*.py'
```

Nur die reinen Runtime-Module können hier direkt gegen TypeScript geprüft
werden. Eine Cocos-spezifische Typprüfung erfordert die durch den Editor
erzeugte `cocos/temp/tsconfig.cocos.json` und das lokale Cocos SDK.

## Abnahmestand

- [x] Authentisches Cocos Creator 3.8.8 Projekt und Editor-Szene eingecheckt.
- [x] Room-/Phone-/Tab-UI im Code vorbereitet; bestehende Editor-Referenzen genutzt.
- [x] Reine Navigation automatisiert testbar; keine neuen Backend-Endpunkte.
- [ ] Cocos Editor importiert alle neuen Dateien ohne Fehler.
- [ ] Room, Smartphone, Tabs, Schließen und Wiederöffnen visuell getestet.
- [ ] Web-Build / Startszene getestet.
- [ ] Optionaler echter Bild-API-Smoke bestätigt.
- [ ] FairyGUI Community getestet (separater Arbeitsschritt).
- [ ] Projektbesitzer hat die UI-Abnahme bestätigt.

Siehe [GAME_SHELL.md](GAME_SHELL.md) für Testmatrix und bekannte Grenzen.
