# ComfyReview

**Status:** Aktive Entwicklung · **Codebasis:** lokale FastAPI-/SQLite-Anwendung für ComfyUI-Bilder · **Langfristige Richtung:** Character Chronicles – schrittweise über POCs, **keine** festgelegte Gesamtarchitektur.

ComfyReview hilft beim **Bewerten, Vergleichen, Kuratieren und Analysieren** generierter Bilder, beim Arbeiten mit Prompt-/LoRA-Katalogen und beim **reproduzierbaren Generieren** über ComfyUI. Der Generator wurde jüngst überarbeitet; Katalog und Datenbank werden weiter optimiert. Das Projekt ist **nicht fertig**.

## Was heute tatsächlich existiert

- **Review / Ranking / Arena / Curation** mit kanonischen Bildidentitäten und zentraler SQLite-Persistenz.
- **Playground / Generator / ComfyUI-Integration** mit Workflow-Blueprint v4, nativer Generierung, Lifecycle und Output-Collection.
- **Prompt-/LoRA-Katalog, Settings und Analytics** sowie Frontend V2 aus Jinja-Templates und nativen JavaScript-Modulen.
- **Canonical SQLite Schema v18 ist im Code implementiert.** Ob die **private** laufende Datenbank bereits den finalen Normalisierungs-/Cutover-Schritt durchlaufen hat, ist daraus **nicht** ableitbar.
- **Card Battler ist derzeit ein aktiver POC**: getestete Mechanik-, Karten-, Entwicklungs- und Visual-Prompt-Bausteine, aber kein vollständig integriertes spielbares Match-/Deck-Frontend.

[Nachweisbarer Code](docs/IMPLEMENTATION_AUDIT.md) · [Kurzstatus](docs/project_status.md) · [Laufende Arbeiten](docs/ACTIVE_WORK.md) · [Card-Battler-POC](docs/pocs/card-battler.md).

## Installation und lokaler Start

**Voraussetzung:** Python 3.11+, für Generatorfunktionen eine erreichbare eigene ComfyUI-Instanz mit den zum Workflow passenden Nodes und Modellen. Für historische Bilder ist gegebenenfalls ein PNG/JSON-Sidecar-Import nötig; **neue kanonische Generatorausgaben benötigen nicht generell ein JSON-Sidecar**.

```bash
python -m venv .venv
```

Umgebung aktivieren: unter Windows `.venv\Scripts\activate`, unter macOS/Linux `source .venv/bin/activate`. Dann:

```bash
pip install -r requirements.txt
python main.py
```

Standardmäßig im Browser: `http://127.0.0.1:8000`.

Konfiguration über [`.env.example`](.env.example), optionale lokale `.env` und Umgebungsvariablen. Zuständig ist **[`comfyreview/settings.py`](comfyreview/settings.py)**, nicht eine frühere `config.py`.

Wichtige Werte:

| Umgebungsvariable | Aufgabe |
| --- | --- |
| `COMFYREVIEW_OUTPUT_ROOT` | Lokales Bildausgabeverzeichnis |
| `COMFYREVIEW_COMFYUI_BASE_URL` | ComfyUI-API-Endpunkt |
| `COMFYREVIEW_WORKFLOWS_DIR` | Workflow-Dateien |
| `COMFYREVIEW_DATABASE` | Kanonische ComfyReview-SQLite-Datei |
| `COMFYREVIEW_PORT` | Lokaler HTTP-Port (Standard 8000) |

**Wichtig bei vorhandenen lokalen Daten:** Startup migriert keine unbekannte alte Datenbank still auf v18. Vor einem Upgrade die [getrennte Betriebs-/Migrationsanleitung](docs/OPERATIONS.md) und [Datenarchitektur](docs/DATA_ARCHITECTURE.md) prüfen. Datenbank, generierte Bilder, Modelle, Geheimnisse und persönliche Pfade gehören **nicht** ins Git-Repository.

## Qualität und Mitwirkung

Für **vollständige lokale Entwicklungstests** werden zusätzlich zu
Python 3.11+ **Node.js 24+**, npm und Playwright Chromium benötigt.
Diese Werkzeuge sind **nicht für den normalen App-Start** erforderlich.

```bash
pip install -r requirements-dev.txt
npm ci
npx playwright install chromium

python -m pytest
python scripts/check_documentation.py
python scripts/quality.py
```

Unter Linux können zusätzliche Chromium-Systembibliotheken erforderlich
sein; die [GitHub-CI](.github/workflows/quality.yml) installiert sie mit
`npx playwright install --with-deps chromium`. Das vollständige Quality-Gate
führt Python-Prüfungen und über `npm run quality` auch ESLint, Prettier,
Stylelint, `checkJs`, Vitest und Playwright aus.

**Automatische Prüfungen und die abschließenden Tests sind getrennt:**
Der **Projektinhaber führt die finalen manuellen Funktions-, UI- und
Provider-Tests selbst durch**, ebenso jede Abnahme an seiner privaten
Datenbank. Ein grüner CI-Lauf für einen konkreten Commit ist technische
Vorprüfung, **keine** stellvertretend erteilte Benutzer- oder
Releasefreigabe. [Code-/CI-Evidenz](docs/IMPLEMENTATION_AUDIT.md) und
[Engineering-Regeln](docs/CODING_STANDARDS.md) beschreiben diese Grenzen.

Code-Änderungen müssen die [Engineering-Regeln](AGENTS.md) beachten. Exports und vollständige Dataset-/LoRA-Verpackung sind nicht als fertig integrierte Produktionspipeline zu behandeln.

## Langfristige Entwicklung

**ComfyReview soll sich zu Character Chronicles entwickeln** – POC- und erfahrungsgetrieben, nicht als starrer Komplettbauplan. Die derzeitige **ungefähre Entwicklungsorientierung** lautet **Card Battler → Timeline → Social Network mit Charakter-Chats → Storyline → Visual-Novel-Content zuletzt**. Die Timeline kann zunächst als eigenständig erprobbarer Einstieg in die spätere Social-Plattform entstehen; das legt keine getrennten Releases fest. **Academy/Schuljahr ist ein möglicher Welt- und Fortschrittsrahmen der Storyline, keine zusätzlich beschlossene Pflichtphase.** Für spätere VN-Inhalte sind Figurenfreistellung, Matting und konsistente Szenenkomposition besondere technische Herausforderungen; begrenzte frühe Machbarkeits-POCs sind möglich.

[Einfaches Zielbild](docs/character-chronicles/vision/README.md) · [Entwicklungslogik](docs/PROJECT_EVOLUTION.md) · [Ausführliche, aber **nicht verbindliche** Quelltexte](docs/character-chronicles/sources/README.md) · [Alte verworfene Chronicle-Technik](docs/character-chronicles/HISTORICAL_CODE_AUDIT.md).

**Keines der älteren „DECIDED“-/M6-/Schema-v58-Dokumente ist dadurch eine heutige Bauvorgabe.** Welche Ideen und technischen Ansätze tatsächlich bleiben, wird explizit anhand der POCs entschieden.

[Dokumentationslandkarte](docs/README.md) · [Offene Entscheidungen](docs/OPEN_DECISIONS.md) · [MIT-Lizenz](LICENSE).
