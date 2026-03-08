<div align="center">

# ComfyReview

**Local review, curation, and analysis for ComfyUI outputs**  
Built for character-focused workflows, especially anime-style generation and later LoRA-oriented curation.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-app-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-local-003B57?logo=sqlite&logoColor=white)
![ComfyUI](https://img.shields.io/badge/ComfyUI-required_workflow-6A5ACD)
![Status](https://img.shields.io/badge/status-0.0.5b-informational)

</div>

> ComfyUI can generate a small mountain of images very quickly.  
> ComfyReview was built to turn that pile into something you can actually **review, compare, curate, and reuse**.

It grew out of a pretty simple problem: once a workflow starts producing large batches of character images, picking the actually good ones turns into its own little boss fight.

Instead of treating that step like endless file cleanup, ComfyReview turns it into a more structured and usable review flow: scan outputs, rate them, compare them, filter them by character and set, keep the generation context attached, and prepare curated selections for later reuse or character LoRA dataset building.

---

## At a glance

| What | Description |
|---|---|
| **Core purpose** | Review and curate ComfyUI generations locally |
| **Best fit** | Character-heavy workflows, especially anime-style image generation |
| **Main input** | PNG files plus matching JSON sidecars |
| **Required dependency** | Included ComfyUI custom node `name_meta_export` |
| **Main views** | Review, Top, Arena, Stats, Playground |
| **Main benefit** | Faster selection, cleaner curation, reproducible reuse |

---

## Why

ComfyUI is excellent at generating images fast. The trouble starts afterwards: lots of variations, lots of prompt tweaks, lots of near-duplicates, and suddenly the selection process becomes its own project.

ComfyReview exists to make that part easier:

- scan local PNG + JSON output pairs
- review images with direct **1–10 ratings** and delete actions
- compare candidates in **Arena-style A/B views**
- filter results by **character** and **set**
- keep prompt and generation context attached to each image
- send selected values back into the **Playground Generator**
- build curated image collections for character-focused **LoRA workflows**

---

## What it does

- **Review** generated images in a local web UI
- **Rate** images on a 1–10 scale
- **Compare** images in pairwise Arena views
- **Filter** by character and set
- **Track** prompts, sampler settings, checkpoint, seed, steps, cfg, scheduler, and denoise values
- **Analyze** local results with SQLite-backed stats pages
- **Reuse** selected generation values in the Playground Generator
- **Maintain** persistent UI state for generator inputs
- **Load** heavier generator-side data lazily to keep the page responsive
- **Update** aggregate views such as Top and Arena through the MV worker path

---

## Required ComfyUI Custom Node

A required part of this workflow is the included ComfyUI custom node **`name_meta_export`**.

ComfyReview depends on sidecar JSON files generated alongside each PNG. Without that JSON output, metadata extraction, statistics, and reproducible generator handoff are not reliable.

**Included in this repository**

- file: `custom_node_for_comfyui/alex_nodes.py`
- required node: `name_meta_export`

**The node is expected to export**

- the rendered PNG
- a JSON sidecar with the same base filename
- prompt text
- KSampler values such as seed, steps, cfg, sampler, scheduler, and denoise
- prompt graph data for later reuse

---

## Main views

| View | Purpose |
|---|---|
| **Review** | Fast rating and delete workflow for image batches |
| **Top** | Aggregated best-image views |
| **Arena** | Pairwise comparison flow |
| **Stats** | Local analysis and breakdown pages |
| **Playground** | Prompt/value handoff back into ComfyUI |

---

## Quick start

### Requirements

- Python 3.11+
- ComfyUI outputs with **PNG + JSON** sidecar files
- the included ComfyUI custom node `name_meta_export`
- a workflow that actually uses `name_meta_export`
- optional: a running ComfyUI instance for Playground Generator features

### Installation

```bash
python -m venv .venv
```

**Windows**

```bash
.venv\Scripts\activate
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Configuration

The current `0.0.5b` source still uses `config.py` as the main source of truth for local paths and server settings.

Before starting the app, check at least:

- `OUTPUT_ROOT`
- `COMFYUI_BASE_URL`
- `WORKFLOWS_DIR`
- `DEFAULT_WORKFLOW_PATH`
- SSL settings if you do not want HTTPS locally

The defaults in `config.py` are development-oriented and should be adjusted for your machine.

### Run

```bash
python main.py
```

Then open the local app in your browser.

---

## Basic workflow

1. Generate images in ComfyUI with the included `name_meta_export` node in the workflow.
2. Save PNG files together with matching JSON sidecars.
3. Point ComfyReview at the correct ComfyUI output folder.
4. Open the local web UI.
5. Review images with ratings, deletes, filters, and Arena comparisons.
6. Use Top, Stats, and Playground pages to reuse and analyze the results.
7. Build curated character/set selections for later dataset or LoRA-oriented work.

---

## Character and set semantics

ComfyReview uses two separate filter axes:

- **Character**
- **Set**

That means views such as **Character = All** and **Set = Face** are meant to work across multiple characters at once.

This matters for character-focused curation workflows, where different images may belong to the same logical set category while still belonging to different characters.

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
├── data/                     # runtime DBs, workflows, UI state
├── custom_node_for_comfyui/  # required ComfyUI custom node
├── tests/                    # test suite
└── README.md
```

---

## Architecture notes

<details>
<summary><strong>Scanner</strong></summary>

The scanner reads PNG/JSON pairs from the ComfyUI output folder, extracts metadata, and upserts the relevant information into the local SQLite-backed app state.

</details>

<details>
<summary><strong>Review flow</strong></summary>

The review side of the app is built to make large batches of similar images easier to work through without turning the whole thing into miserable manual sorting.

</details>

<details>
<summary><strong>Generator reuse</strong></summary>

The Playground Generator is designed to carry values back into ComfyUI in a reproducible way instead of relying on vague memory and copy-paste archaeology.

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

The repository also includes sample PNG/JSON files that can be used as scanner input for local testing.

---

## Current status

This README reflects the current **`0.0.5b`** line in the repository.

**Current focus**

- stable local review flow
- modularized Playground Generator structure
- character/set-based curation semantics
- local SQLite-backed analysis and aggregate pages
- ComfyUI integration through the required metadata-export workflow

**Not the goal of this version**

- a fully redesigned data identity model
- full separation of curation truth from physical folder layout
- a final export or packaging architecture for future LoRA dataset builds

---

## Contributing

If you change behavior in this project, try not to silently break the things that make the workflow usable in practice:

- the required PNG + JSON pairing
- character/set filtering semantics
- generator state persistence
- lazy loading behavior in generator-related views
- reproducible value handoff back into ComfyUI

---

