<div align="center">

# ComfyReview

**Local review, curation, and analysis for ComfyUI outputs**  
Built for character-focused image workflows, especially anime-style generation and later LoRA-oriented curation.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-local_app-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-local-003B57?logo=sqlite&logoColor=white)
![ComfyUI](https://img.shields.io/badge/ComfyUI-metadata_workflow-6A5ACD)
![Status](https://img.shields.io/badge/status-public_prototype-informational)

</div>

> ComfyUI can generate a small mountain of images very quickly.  
> ComfyReview helps turn that pile into something you can actually review, compare, curate, analyze, and reuse.

ComfyReview is a local FastAPI and SQLite web app for reviewing AI-generated image batches from ComfyUI. It grew out of a practical workflow problem: once a character-focused ComfyUI setup starts producing large batches of variations, selecting the useful images becomes its own time-consuming process.

Instead of treating that step like endless file cleanup, ComfyReview turns it into a structured review flow: scan outputs, rate images, compare candidates, filter by character and set, keep generation context attached, and prepare curated selections for later reuse or LoRA-oriented dataset building.

---

## Project status

ComfyReview is a public prototype and local workflow tool.

The current repository demonstrates a usable local review system with image scanning, rating, filtering, statistics, Arena comparison, Playground handoff, SQLite persistence and a required ComfyUI metadata export node.

It should not be treated as a polished packaged desktop application. The project is best understood as a practical tool and portfolio project that documents a real local AI workflow.

For a more detailed scope overview, see:

```text
docs/project_status.md
```

---

## At a glance

| What | Description |
|---|---|
| **Core purpose** | Review and curate ComfyUI generations locally |
| **Best fit** | Character-heavy workflows, especially anime-style image generation |
| **Main input** | PNG files plus matching JSON sidecars |
| **Required dependency** | Included ComfyUI custom node `name_meta_export` |
| **Main views** | Review, Top, Arena, Stats, Playground |
| **Storage** | Local SQLite databases |
| **Main benefit** | Faster selection, cleaner curation, reproducible reuse |

---

## Why

ComfyUI is excellent at generating images fast. The trouble starts afterwards: lots of variations, lots of prompt tweaks, lots of near-duplicates, and suddenly the selection process becomes its own project.

ComfyReview exists to make that part easier:

- scan local PNG and JSON output pairs
- review images with direct 1 to 10 ratings and delete actions
- compare candidates in Arena-style A/B views
- filter results by character and set
- keep prompt and generation context attached to each image
- send selected values back into the Playground Generator
- build curated image collections for character-focused LoRA workflows

---

## What it does

- Review generated images in a local web UI
- Rate images on a 1 to 10 scale
- Compare images in pairwise Arena views
- Filter by character and set
- Track prompts, sampler settings, checkpoint, seed, steps, cfg, scheduler and denoise values
- Analyze local results with SQLite-backed stats pages
- Reuse selected generation values in the Playground Generator
- Maintain persistent UI state for generator inputs
- Load heavier generator-side data lazily to keep the page responsive
- Update aggregate views such as Top and Arena through the MV worker path

---

## Required ComfyUI custom node

A required part of this workflow is the included ComfyUI custom node **`name_meta_export`**.

ComfyReview depends on sidecar JSON files generated alongside each PNG. Without that JSON output, metadata extraction, statistics, filtering and reproducible generator handoff are not reliable.

**Included in this repository**

```text
custom_node_for_comfyui/alex_nodes.py
```

**Required node**

```text
name_meta_export
```

The node is expected to export:

- the rendered PNG
- a JSON sidecar with the same base filename
- prompt text
- KSampler values such as seed, steps, cfg, sampler, scheduler and denoise
- prompt graph data for later reuse

---

## Main views

| View | Purpose |
|---|---|
| **Review** | Fast rating and delete workflow for image batches |
| **Top** | Aggregated best-image views |
| **Arena** | Pairwise comparison flow |
| **Stats** | Local analysis and breakdown pages |
| **Playground** | Prompt and value handoff back into ComfyUI |

---

## Quick start

### Requirements

- Python 3.11+
- ComfyUI outputs with PNG and JSON sidecar files
- the included ComfyUI custom node `name_meta_export`
- a ComfyUI workflow that actually uses `name_meta_export`
- optional: a running ComfyUI instance for Playground Generator features

### Installation

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Configuration

ComfyReview is configured through `config.py` and optional environment variables.

The default paths are development-oriented and safe for a fresh clone, but they should be adjusted for your local ComfyUI setup before serious use.

Important settings:

| Setting | Environment variable | Purpose |
|---|---|---|
| `OUTPUT_ROOT` | `COMFYREVIEW_OUTPUT_ROOT` | Folder scanned for PNG and JSON output pairs |
| `COMFYUI_BASE_URL` | `COMFYREVIEW_COMFYUI_BASE_URL` | Local ComfyUI API URL |
| `WORKFLOWS_DIR` | `COMFYREVIEW_WORKFLOWS_DIR` | Folder for workflow files |
| `DEFAULT_WORKFLOW_PATH` | `COMFYREVIEW_DEFAULT_WORKFLOW` | Default workflow used by Playground features |
| `DATA_DIR` | `COMFYREVIEW_DATA_DIR` | Local runtime data folder |
| `SSL_ENABLED` | `COMFYREVIEW_SSL_ENABLED` | Enables local HTTPS when configured |

Example on Windows PowerShell:

```powershell
$env:COMFYREVIEW_OUTPUT_ROOT="D:\ComfyUI\output"
$env:COMFYREVIEW_COMFYUI_BASE_URL="http://127.0.0.1:8188"
python main.py
```

### Run

```bash
python main.py
```

Then open the local app in your browser. By default, the app runs on:

```text
http://127.0.0.1:8000
```

---

## Basic workflow

1. Install the included `name_meta_export` custom node in ComfyUI.
2. Use a workflow that saves PNG files together with matching JSON sidecars.
3. Point ComfyReview at the correct ComfyUI output folder.
4. Start ComfyReview locally.
5. Open the local web UI.
6. Review images with ratings, deletes, filters and Arena comparisons.
7. Use Top, Stats and Playground pages to reuse and analyze the results.
8. Build curated character and set selections for later dataset or LoRA-oriented work.

---

## Character and set semantics

ComfyReview uses two separate filter axes:

- Character
- Set

That means views such as **Character = All** and **Set = Face** are meant to work across multiple characters at once.

This matters for character-focused curation workflows, where different images may belong to the same logical set category while still belonging to different characters.

---

## Local-first design

ComfyReview is designed as a local tool.

- Images are scanned from local folders
- Ratings and derived data are stored in local SQLite databases
- Runtime state and generated databases are intentionally ignored by Git
- ComfyUI integration expects a local or user-controlled ComfyUI instance
- No cloud service is required for the core review workflow

The repository is not intended to contain private image outputs, model files, personal ComfyUI paths, certificates, keys or runtime databases.

---

## Project structure

```text
ComfyReview/
├── app.py
├── main.py
├── config.py
├── scanner.py
├── routers/                  # page routes and API endpoints
├── services/                 # business logic
├── stores/                   # SQLite access and persistence helpers
├── templates/                # HTML templates
├── static/                   # CSS, JS, assets
├── data/                     # local runtime data, ignored where needed
├── custom_node_for_comfyui/  # required ComfyUI custom node
├── tests/                    # test suite
└── README.md
```

---

## Architecture notes

<details>
<summary><strong>Scanner</strong></summary>

The scanner reads PNG and JSON pairs from the ComfyUI output folder, extracts metadata, and upserts the relevant information into the local SQLite-backed app state.

</details>

<details>
<summary><strong>Review flow</strong></summary>

The review side of the app is built to make large batches of similar images easier to work through without turning the whole thing into manual sorting work.

</details>

<details>
<summary><strong>Generator reuse</strong></summary>

The Playground Generator is designed to carry values back into ComfyUI in a reproducible way instead of relying on memory and manual copy-paste.

</details>

<details>
<summary><strong>MV worker</strong></summary>

Aggregate-style views such as Top and Arena are not just static file listings. They depend on the app's worker/update path and the local derived data it maintains.

</details>

---

## Testing

Run the test suite with:

```bash
pytest
```

The repository may include sample PNG and JSON files that can be used as scanner input for local testing.

---

## Known limitations

- This is a local prototype, not a packaged desktop application
- Configuration still requires direct path and environment setup
- The metadata workflow depends on the included ComfyUI custom node
- The app assumes PNG and JSON sidecar pairs for reliable metadata handling
- Export and dataset-building workflows are not final production pipelines
- The data identity model is still tied to the current local workflow assumptions
- Public documentation may lag behind internal workflow experiments

---

## Not the goal of this version

- Fully redesigned data identity model
- Full separation of curation truth from physical folder layout
- Final export or packaging architecture for future LoRA dataset builds
- Multi-user hosting
- Cloud deployment
- Public SaaS operation

---

## Contributing

This is primarily a personal local workflow tool, but the public repository documents the approach and implementation.

If you change behavior in this project, avoid silently breaking the workflow assumptions that make the app useful in practice:

- required PNG and JSON pairing
- character/set filtering semantics
- generator state persistence
- lazy loading behavior in generator-related views
- reproducible value handoff back into ComfyUI
- local-first runtime data separation

---

## License

The project code is licensed under the MIT License. See `LICENSE`.
