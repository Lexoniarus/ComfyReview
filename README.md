# ComfyReview

ComfyReview is a local review, curation, and analysis tool for ComfyUI outputs.

It grew out of a pretty simple problem: once a workflow starts producing large batches of character images, picking the actually good ones turns into its own little boss fight.

The project is mainly built for character-focused workflows, especially anime-style image generation. It helps scan PNG + JSON output pairs, rate and compare images, filter them by character and set, preserve generation context, and prepare curated selections for later reuse or character LoRA dataset building.

Instead of treating that step like endless file cleanup, ComfyReview turns it into a more structured and usable review flow.

## Why

ComfyUI is great at generating images fast. But once you have many characters, variations, prompt changes, and runs, reviewing everything becomes a project of its own.

ComfyReview exists to make that part easier:

- scan local PNG + JSON output pairs
- review images with direct 1–10 ratings and delete actions
- compare candidates in Arena-style A/B views
- filter results by character and set
- keep prompt and generation context attached to each image
- send selected values back into the Playground Generator
- build curated image collections for character-focused LoRA workflows

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

## Required ComfyUI Custom Node

A required part of this workflow is the included ComfyUI custom node `name_meta_export`.

ComfyReview depends on sidecar JSON files generated alongside each PNG. Without that JSON output, metadata extraction, statistics, and reproducible generator handoff are not reliable.

Included in this repository:

- file: `custom_node_for_comfyui/alex_nodes.py`
- required node: `name_meta_export`

The node is expected to export:

- the rendered PNG
- a JSON sidecar with the same base filename
- prompt text
- KSampler values such as seed, steps, cfg, sampler, scheduler, and denoise
- prompt graph data for later reuse

## Main Views

ComfyReview currently revolves around a few main views:

- **Review** for direct image rating and delete actions
- **Top** for aggregated best-image views
- **Arena** for pairwise comparison
- **Stats** for local analysis pages
- **Playground** for generator-side reuse and prompt/value handoff back into ComfyUI

## Quick Start

### Requirements

- Python 3.11+
- ComfyUI outputs with PNG + JSON sidecar files
- the included ComfyUI custom node `name_meta_export`
- a workflow that actually uses `name_meta_export`
- optional: a running ComfyUI instance for Playground Generator features

### Installation

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

Install dependencies:

```bash
pip install -r requirements.txt
```

### Configuration

The current 5b source still uses `config.py` as the main source of truth for local paths and server settings.

Before starting the app, check at least:

- `OUTPUT_ROOT`
- `COMFYUI_BASE_URL`
- `WORKFLOWS_DIR`
- `DEFAULT_WORKFLOW_PATH`
- SSL settings if you do not want HTTPS locally

The defaults in `config.py` are local development values and should be adjusted for your machine.

### Run

```bash
python main.py
```

Then open the app in your browser. The default source tree includes settings for local FastAPI startup via `uvicorn` from `main.py`.

## Basic Workflow

1. Generate images in ComfyUI with the included `name_meta_export` node in the workflow.
2. Save PNG files together with matching JSON sidecars.
3. Point ComfyReview at the correct ComfyUI output folder.
4. Open the local web UI.
5. Review images with ratings, deletes, filters, and Arena comparisons.
6. Use Top, Stats, and Playground pages to reuse and analyze the results.
7. Build curated character/set selections for later dataset or LoRA-oriented work.

## Character and Set Semantics

ComfyReview uses two separate filter axes:

- **Character**
- **Set**

That means views such as **Character = All** and **Set = Face** are meant to work across multiple characters at once.

This matters for character-focused curation workflows, where different images may belong to the same logical set category while still belonging to different characters.

## Project Structure

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

## Architecture Notes

### Scanner

The scanner reads PNG/JSON pairs from the ComfyUI output folder, extracts metadata, and upserts the relevant information into the local SQLite-backed app state.

### Review Flow

The review side of the app is built to make large batches of similar images easier to work through without turning the whole thing into miserable manual sorting.

### Generator Reuse

The Playground Generator is designed to carry values back into ComfyUI in a reproducible way instead of relying on vague memory and copy-paste archaeology.

### MV Worker

Aggregate-style views such as Top and Arena are not just static file listings. They depend on the app's worker/update path and the local derived data it maintains.

## Testing

Run the test suite with:

```bash
pytest
```

## Current Status

This README reflects the current `0.0.5b` line in the repository.

Current focus:

- stable local review flow
- modularized Playground Generator structure
- character/set-based curation semantics
- local SQLite-backed analysis and aggregate pages
- ComfyUI integration through the required metadata-export workflow

Not the goal of this version:

- a fully redesigned data identity model
- full separation of curation truth from physical folder layout
- a final export/packaging architecture for future LoRA dataset builds

## Notes

- The repository includes sample PNG/JSON files that can be used as scanner input for testing.
- Local database files are created as needed.
- Some current defaults are clearly development-oriented and may need cleanup before broader distribution.

## Contributing

If you change behavior in this project, try not to silently break the things that make the workflow usable in practice:

- the required PNG + JSON pairing
- character/set filtering semantics
- generator state persistence
- lazy loading behavior in generator-related views
- reproducible value handoff back into ComfyUI

## License

Add your license here.
