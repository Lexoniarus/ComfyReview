# ComfyReview

Version: 0.0.5b

ComfyReview ist eine lokale FastAPI-Web-App zur Bewertung, Sichtung und Analyse von ComfyUI-Outputs. Der Schwerpunkt liegt auf reproduzierbaren Runs, SQLite-basierter Auswertung und einem Playground, der atomare Render-Settings und Prompts zuverlässig an ComfyUI übergibt.

Der aktuelle 5b-Stand ist die modularisierte Weiterentwicklung von 5a. Die Architektur wurde in kleinere, besser lesbare Verantwortungsbereiche aufgeteilt, ohne die bestehende 5b-Semantik für Scanner, Review, Curation und Playground aufzugeben.

## Quickstart

### 1) Environment anlegen

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 2) Dependencies installieren

```bash
pip install -r requirements.txt
```

### 3) Optional: Konfiguration setzen

Die Defaults laufen lokal ohne SSL auf `127.0.0.1:8000`.

Wenn ein bestehender ComfyUI-Output-Ordner verwendet werden soll:

```bash
set COMFYREVIEW_OUTPUT_ROOT=C:\Path\To\ComfyUI\output
```

Weitere Variablen stehen in `.env.example`.

### 4) Start

```bash
python main.py
```

## Testen

```bash
pytest
```

## Was 5b fachlich abbildet

### Review und Ratings
- Bilder werden gescannt, mit Sidecar-JSON verknüpft und als reviewbare Items aufbereitet.
- Ratings werden run-bezogen gespeichert.
- SQLite ist die lokale Source of Truth für Auswertung, Worker-Läufe und Playground-bezogene Hilfsdaten.

### Character- und Set-Semantik
- Character und Set sind getrennte Filterdimensionen.
- `Character = All` aggregiert über Characters hinweg.
- `Set = face` filtert fachlich auf das Set `face`, unabhängig davon, ob mehrere Characters beteiligt sind.
- Diese Semantik ist in 5b bewusst erhalten und nicht Teil eines Cleanup-Refactors.

### Scanner-Semantik
- Der Scanner arbeitet auf realen Output-Dateien und Sidecar-JSONs.
- Für den UI-Kontext wird der Character-Scope logisch vom Pfad abgeleitet, statt reine Unterordner blind als eigenständige Characters zu behandeln.
- Hilfs- und Exportpfade wie `_trash` oder `_lora_export` sollen nicht als reguläre Review-Inhalte behandelt werden.

### Playground Generator
- Der Generator wurde gegenüber 5a bewusst in kleinere Verantwortungsbereiche aufgeteilt.
- UI-State bleibt über State-Dateien stabil, damit Formwerte nach Submit oder Reload nicht ständig verloren gehen.
- Teurere Auflösungen, etwa Best-Picture-Zuordnungen pro Draft, werden lazy geladen, damit die Seite schnell initial rendern kann.
- Diese Zerlegung ist gewollte 5b-Architektur und kein Rückbaukandidat.

## Architekturüberblick

### Einstiegspunkte
- `main.py` startet die App.
- `app.py` baut FastAPI, Router und Hintergrunddienste zusammen.

### Router
- `routers/index_router.py`
- `routers/top_router.py`
- `routers/stats_router.py`
- `routers/arena_router.py`
- `routers/playground/*`

### Zentrale Services
- `services/review_page_service.py`
- `services/rating_submission_service.py`
- `services/gallery_view_service.py`
- `services/analytics_page_service.py`
- `services/mv_worker.py` plus `services/mv_worker_core/*`
- `services/playground_generator_core/*`
- `services/playground_generator_ui/*`
- `services/comfy_client_core/*`
- `services/context_filters.py`
- `services/curation_assignment_service.py`

### Stores / SQLite-Zugriff
- `stores/*` kapseln datenbankspezifische Zugriffe.
- Dazu gehören unter anderem Ratings, Images, Prompt-Daten, MV-Worker-State und Curation.

## Wichtige Grenzen des aktuellen 5b-Stands

Der aktuelle 5b-Stand ist **kein** Umbau auf ein komplett neues Datenmodell. Insbesondere gilt weiterhin:

- Curation, Set-Zuordnung und physischer Dateipfad sind noch eng miteinander verbunden.
- Path-Relinking und Dateibewegungen gehören zur aktuellen Semantik und sind nicht versehentlich „wegzuvereinfachen“.
- Eine zukünftige Version kann diese Kopplung sauberer entkernen, aber das ist nicht Teil des 5b-Cleanups.

Mit anderen Worten: 5b ist modularer als 5a, bleibt aber fachlich bewusst kompatibel mit der bestehenden Arbeitsweise.

## Hinweise für lokale Repos

- Die App erzeugt SQLite-Dateien bei Bedarf automatisch.
- Lokale DBs, Zertifikate und andere maschinenspezifische Artefakte sollten nicht committed werden.
- Eine `.gitignore` für solche Dateien gehört ins Repo und sollte aktiv gepflegt werden.
