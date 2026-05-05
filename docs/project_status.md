# Project Status

## Summary

ComfyReview is a public prototype and local workflow tool for reviewing, curating and analyzing ComfyUI image outputs.

The project exists because large AI image batches quickly become difficult to review manually. ComfyReview provides a structured local review workflow with ratings, filtering, Arena-style comparisons, statistics, local SQLite storage and generator value handoff.

## Public framing

Recommended repository framing:

```text
Local FastAPI tool for reviewing, curating and analyzing ComfyUI image outputs with ratings, filters, Arena comparisons, SQLite stats and Playground handoff.
```

The project should be presented as a practical local AI workflow tool and portfolio project, not as a polished commercial desktop application.

## Current status

The current repository demonstrates a usable local workflow around ComfyUI outputs.

Implemented areas include:

- local FastAPI web app
- SQLite-backed persistence
- PNG and JSON sidecar scanning
- image review and rating flow
- character and set filtering
- Top and aggregate views
- Arena-style image comparison
- Stats and analysis pages
- Playground handoff back toward ComfyUI
- included ComfyUI custom node for metadata export
- pytest-based test setup

## Workflow assumptions

ComfyReview currently expects a specific local workflow:

- ComfyUI generates PNG files
- the included `name_meta_export` node creates matching JSON sidecars
- image outputs are stored in a local output folder
- ComfyReview scans that folder and stores derived data in local SQLite databases
- runtime databases, certificates, keys and private image output folders should not be committed

## Local-first scope

The application is designed as a local-first tool.

It is not intended to be:

- a hosted SaaS product
- a multi-user web service
- a cloud image platform
- a finished desktop installer
- a full production LoRA dataset manager

## Known limitations

Known limitations of the current public prototype:

- setup still requires direct local path configuration
- metadata extraction depends on the included ComfyUI custom node
- PNG and JSON sidecar pairs are expected for reliable behavior
- export and dataset-building logic is not a final production pipeline
- physical folder layout still influences parts of the workflow
- documentation may lag behind experimental internal workflow ideas

## Good public indicators

The project is useful as a public portfolio repository because it demonstrates:

- practical Python application structure
- FastAPI routing and local web UI organization
- SQLite-backed local persistence
- workflow-oriented AI tooling
- integration with an external local AI tool, ComfyUI
- clear separation between source code and runtime data
- documentation of assumptions and limitations

## Suggested next polish tasks

Useful future cleanup tasks, if the project is polished further:

- add screenshots or a short GIF to the README
- add a small sample workflow diagram
- add a minimal example output pair for scanner testing, only if legally and personally safe
- pin dependency versions more tightly for reproducible installs
- add a `.env.example` file for common local configuration values
- add GitHub Actions for running tests

## License

Project code is licensed under the MIT License. See `LICENSE`.
