# ComfyReview

Version: 0.0.5b Unstable

ComfyReview ist eine lokale FastAPI Web App zur Bewertung und Analyse von ComfyUI Outputs. Der Fokus liegt auf reproduzierbaren Runs, SQLite basierter Auswertung und einem Playground, der atomare Render Settings und Prompts zuverlässig an ComfyUI übergibt.

## Quickstart

1) Environment anlegen

```bash
python -m venv .venv
```

Windows

```bash
.venv\Scripts\activate
```

macOS Linux

```bash
source .venv/bin/activate
```

2) Dependencies installieren

```bash
pip install -r requirements.txt
```

3) Optional: Konfiguration setzen

Die Defaults laufen lokal ohne SSL auf `127.0.0.1:8000`.

Wenn du einen bestehenden ComfyUI Output Ordner mounten willst, setze:

```bash
set COMFYREVIEW_OUTPUT_ROOT=C:\\Path\\To\\ComfyUI\\output
```

Weitere Variablen findest du in `.env.example`.

4) Start

```bash
python main.py
```

## Tests

```bash
pytest
```

## Hinweise

Die App erzeugt SQLite Dateien bei Bedarf automatisch. In einem Git Repo sollten lokale DBs und Zertifikate nicht committed werden, dafür ist eine `.gitignore` enthalten.
