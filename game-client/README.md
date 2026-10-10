# Character Chronicles – Game-Client

**Status:** `WORKING_DIRECTION / CANDIDATE` · **Start:** 2026-10-10  
**Arbeitsbranch:** `feature/character-chronicles-game-client` · **Ausgangsbasis:** `refactor/review-boundary`

## Ziel und Grenze

Hier soll schrittweise ein **eigenständiges, spielerisch gestaltetes Frontend** für
Character Chronicles entstehen. Das bisherige ComfyReview-Frontend in
`templates/` und `static/` bleibt vorerst ausdrücklich als
**Entwicklungs-/Studiooberfläche** erhalten.

Das neue Frontend ist **kein zweiter Backend-Core**: Python/FastAPI bleibt
für fachliche Entscheidungen, Canon, Persistenz, Generierung und externe
Provider zuständig. Der Game-Client stellt bestätigte Zustände dar,
nimmt Spielereingaben entgegen und inszeniert die Ergebnisse.

Die aktuelle Produktwelt ist in
[`docs/character-chronicles/vision/world.md`](../docs/character-chronicles/vision/world.md)
beschrieben: Kobe ab 2032, eine zweijährige postsekundäre Academy für Erwachsene,
soziale Charakterinteraktionen, eine etablierte Social-/Kartenkultur und
langfristig eine erzählerisch zentrale VN. Die Umsetzung bleibt iterativ.

## Vorläufige technische Richtung

| Ebene | Arbeitsannahme | Stand |
| --- | --- | --- |
| Spielclient | **Cocos Creator 3.8.x + TypeScript** | Zielkandidat, noch kein Editorprojekt angelegt |
| UI-Gestaltung | Cocos UI; **FairyGUI Community** als bevorzugte Ergänzung | Versions-/Integrations-Smoke offen |
| Entwicklungswerkzeuge | Cocos Editor, VS Code, Node.js/npm, Codex/ChatGPT | Noch keine neue Game-Client-Toolchain abgenommen |
| Fachlogik und API | Vorhandener **Python-/FastAPI-Core** | Beibehalten; neue Game-APIs nur bei tatsächlichem Bedarf |
| Bildgenerierung | Vorhandene ComfyUI-Provider-/Generierungsgrenzen | Vorhandene Infrastruktur nutzen; Game-Asset-Pipeline noch offen |
| Datenhaltung | Kanonischer Python-Backend-Datenbestand | Keine zweite lokale Spielwahrheit im Client |
| Erstplattform | PC/Laptop | Browser/iPad optional; Steam gegenwärtig nicht eingeplant |

**Wichtig:** Cocos Creator nutzt Node.js unter anderem im Entwicklungs-/
Editor-Ökosystem. Das bedeutet **nicht**, dass der Python-Core ersetzt oder
für den fertigen Client ein Node.js-Backend eingeführt wird.

FairyGUI Community darf in kommerziellen Spielen verwendet werden und unterstützt
manuellen UI-Paketexport. Der kostenpflichtige Kommandozeilenexport ist
**keine Voraussetzung für Runtime-Asset-Loading**. Trotzdem wird FairyGUI
erst nach einem erfolgreichen Cocos-Kompatibilitätstest eine feste Abhängigkeit.

## Inhaltliche Trennung: feste UI und generierte Inhalte

- **Feste, mitgelieferte Darstellung:** UI, Smartphone-Hülle, App-Navigation,
  Kartenrahmen, Booster-/Kampfeffekte und gegebenenfalls ein Academy-Raum als
  wiedererkennbarer interaktiver Hub.
- **Dynamische Assets:** Figurenporträts, Profilbilder, Kartenillustrationen,
  später VN-Figuren und weitere freigegebene Szenenassets. Sie erhalten
  fachliche IDs/Versionen im Python-Core und werden **zur Laufzeit** geladen.
- **Dynamische Texte:** Posts, Chats, KI-generierte Antworten und Dialoge
  müssen in vorbereitete UI-Komponenten eingebunden werden können.
- **Animation ist Darstellung:** Karten-/Booster-/Kampf-/VN-Animationen
  verändern nicht eigenständig den autoritativen Spielzustand.
- **Checkpoint-Unabhängigkeit:** Feste UI/Umgebung braucht eine eigene,
  animekompatible Designsprache; sie darf nicht von NetaYume oder einem
  bestimmten späteren Modell abhängig sein.

**Asset-Regel:** LimeZu wird **nicht** verwendet. Kenney und andere fremde
Quellen werden **Asset für Asset** auf Stil, Lizenz, kommerzielle Einbettung
und gegebenenfalls KI-Eingaben geprüft. Fremdgrafik und automatisch generierte
Bilder gehören nicht ungeprüft in Git.

## Was der aktuelle Backend-Stand bereits hergibt

Review, Ranking, Arena (Bildvergleich), Generator/ComfyUI, Katalog,
Generationshistorie und die dazugehörigen API-v2-Routen existieren.
Insbesondere `GET /api/v2/images/{image_uid}` liefert kanonischen
Bildkontext, über den sich ein erstes Runtime-Asset-Experiment anbinden lässt.

**Nicht vorhanden oder nicht integriert:** Ein vollständiges Card-Crafting-
/Collection-/Deck-/PvE-/PvP-HTTP-Game-API, eine Story-/Social-/VN-Runtime
oder ein fertiges Asset-Readiness-System. Hierfür keine fiktiven
Produktionsschnittstellen voraussetzen. Die tatsächliche Code-Evidenz steht in
[`docs/IMPLEMENTATION_AUDIT.md`](../docs/IMPLEMENTATION_AUDIT.md)
und [`docs/pocs/card-battler.md`](../docs/pocs/card-battler.md).

## Nächste abgegrenzte Arbeitsschritte (keine starre Release-Roadmap)

1. **Editor-Basis prüfen:** Cocos Creator 3.8.x im Editor ein neues
   TypeScript-2D-Projekt erstellen; dessen originale Projekt-/Metadateien
   versionieren. Keine künstlichen `.scene`-/Prefab-Dateien von Hand erzeugen.
2. **Ein kleines echtes Game-Fenster:** eine minimale Szene mit Layout,
   Skalierung, Eingabe, Audio-/Animations-Grundlage und klar gekennzeichneten
   Platzhaltergrafiken.
3. **FairyGUI-Kompatibilität prüfen:** UI-Paket in Community manuell exportieren,
   in genau diesem Cocos-Projekt laden; dynamisches Avatarbild, Scrollliste,
   Text und Eingabefeld mit dem vorgesehenen UI-Layer testen. Nicht geeignet?
   Cocos-eigenes UI prüfen statt eine Abhängigkeit zu erzwingen.
4. **Backend-Smoke:** Cocos-Client bezieht mindestens ein freigegebenes Bild
   über die bestehende Python-API. Lade-, Fehler-, Wechsel- und
   Ressourcenfreigabe-Pfade verifizieren. Keine Tests mit privaten Bildern
   oder Dateien in Git einchecken.
5. **Szenen-/Assetvertrag:** feste interaktive Hub-/Smartphone-Vorlage mit
   Mock-Daten gegenüber versionierten Runtime-Assets abgrenzen; die
   Academy-Raumgestaltung bleibt bis zur Asset-Auswahl offen.
6. **Gameplay-Flows später anbinden:** zuerst zum tatsächlich integrierten
   Card-Battler-POC passend, nicht anhand historischer Regeln oder erfundener
   Booster-/Liga-/VN-Endpunkte.

Bei jedem Schritt gelten die bestehenden Engineering- und
[Entscheidungsregeln](../docs/DECISION_POLICY.md). Cocos-/FairyGUI-
Verfügbarkeit, Grafikqualität und Bedienbarkeit sind erst nach echten
Builds und Nutzerabnahme belegt.

## Nicht Teil dieses Startschritts

- Kein Umbau/Abschalten des bestehenden Frontend V2.
- Keine Änderung von Python-Domäne, SQLite-Schema oder ComfyUI-Provider.
- Keine verbindlichen neuen Card-Battler-Regeln, Welt-Screens oder
  UI-Lizenz-/Assetfreigaben.
- Kein Steam-Release, Abo-/Cloud-Deployment oder erzwungener iPad-Support.
- Kein bereits fertiger oder laufender Cocos-Spielclient.

Die Branch markiert eine **isolierte Arbeitsfläche**. Die erste ausführbare
Cocos-Szene entsteht regulär im Cocos Creator Editor.


## Vorbereiteter Editor-/API-Smoke (noch kein Cocos-Projekt)

- [Einrichtung, Cocos-Editor-Schritte und Abnahmestatus](SETUP.md)
- `starter/assets/scripts/CanonicalImagePreview.ts`: Cocos-3.8-Komponente für ein zur Laufzeit geladenes kanonisches Bild
- `starter/assets/scripts/runtime/ComfyReviewImageApi.ts`: getestete, Cocos-unabhängige HTTP-/Bildreferenz-Grenze
- `scripts/install_starter.py`: kopiert TypeScript erst **nach** der Cocos-Dashboard-Projekterstellung; keine handgemachten `.scene`/`.prefab`/`.meta`
- `scripts/dev_proxy.py`: nur lokaler Same-Origin-Web-Smoke ohne FastAPI-CORS-Änderung
- `tests/`: Tests für API-Validierung, Skriptinstallation und Proxy

**Nachgewiesen:** lokale TypeScript-Typprüfung, 8 Node-Tests und 5 Python-Tests bestanden.  
**Noch offen:** echte Cocos-Editor-Import-/Build-Abnahme, FairyGUI-Kompatibilität und Native-Smoke; der Editor ist in der Ausführungsumgebung nicht installiert.

## Weiterführend: erste Game Shell

Für den ersten sichtbar spielähnlichen Client ist nun
[GAME_SHELL.md](GAME_SHELL.md) ergänzt: ein Cocos-editorbasiertes Zimmer,
ein ausklappbares Smartphone mit drei navigierbaren Ansichten und ein
**dynamisch geladenes kanonisches Demo-Bild** im Nachrichtenpanel.
Die TypeScript-Navigation wird headless getestet; die Editor-/FairyGUI-
Integration ist weiterhin offen und darf nicht als bestanden gelten.

Alle neuen Dateien liegen ausschließlich unter `game-client/`.
