# ComfyReview Frontend V2 Design Contract

Status: accepted implementation reference on `refactor/review-boundary`,
2026-10-01.

## Product frame

Frontend V2 is a desktop-oriented creative and analysis tool for anime image
production. Its stable spatial language is:

```text
LEFT   = scope
CENTER = image or active work
RIGHT  = context
```

The center remains visually dominant. The interface uses the proven V1 dark
navy canvas with restrained cyan and green ambient light, deep working
surfaces, fine dividers and explicit semantic color. V2 keeps its calmer
editorial spacing and component hierarchy; the light warm-gray experiment was
rejected after comparison with the running V1 product.

The accepted layout reference is
`docs/design/frontend-v2/top-worst-reference.png`. It fixes density,
three-region composition, image treatment and component character. The color
reference is the V1 token set preserved in the Git history and implemented in
`static/css/v2/tokens.css`. The generated sample data is not product copy and
is not an implementation fixture.

## Allowed primary navigation copy

The application bar contains only:

```text
ComfyReview
Prüfen
Top / Worst
Arena
Playground
Katalog
Generierungen
Analysen
```

The generated reference's Japanese claim, user avatar, global search,
grid/list toggle and ranking sort control are intentionally not part of the
product. Scope search remains available inside the Scope Navigator. A labelled
settings control on the right side of the application bar is part of the
product and opens the dedicated `/settings` surface.

## Typography and geometry

- UI family: `Segoe UI Variable Text`, `Segoe UI`, system UI fallback.
- Editorial headings use the same family with tighter tracking and stronger
  weight rather than introducing a decorative display font.
- Base UI text is 14 px with 20 px line height. Dense labels are 12 px with
  16 px line height. Controls never inherit browser-default typography.
- The application bar is 56 px high. On wide screens the Scope Navigator is
  256 px and the Image Inspector is 360 px.
- Surfaces use 6-10 px radii, fine neutral borders and restrained shadows.
  Large nested rounded cards and glass effects are prohibited.
- Images have no color overlay. Cards use edge-to-edge media with a narrow
  factual footer.

## Color contract

The canonical tokens live in `static/css/v2/tokens.css`. Scope color is never
the sole carrier of meaning: every scope also has a text label and a consistent
icon or shape.

Character is visually strongest. Scope colors and lifecycle/status colors are
separate systems. Error, running, completed and attention states must not reuse
scope colors as their only cue.

## Reusable component families

- application bar and primary navigation;
- Scope Navigator, scope group, scope value and removable active-scope chip;
- secondary filter field and segmented mode switch;
- image grid, image card and selected-card state;
- Image Inspector with Context, Prompt, Generierung, Workflow and Bewertungen;
- image viewer dialog;
- buttons, fields, tabs, dividers, loading, empty and error states;
- drawers and rail-collapse controls.

## Settings surface

Settings uses the same dark navy shell and compact editorial hierarchy as the
other V2 surfaces. A narrow section navigator remains visible beside one
focused form region; settings are not spread across modal dialogs.

The surface contains General, Generation profiles, Review, Curation, ComfyUI,
and Storage and database sections. General preferences and generation profiles
are live canonical data. Environment-derived infrastructure settings are
read-only, name their controlling environment variable, and state when a
restart is required. The browser never writes `.env`.

Generation profiles own reproducible sampler defaults and an ordered LoRA
stack with separate model and CLIP strengths. Review and Curation settings are
UI/session defaults only and do not change review-event or assignment
semantics.

## Collection and evidence contract

Analytics collections render at most 24 records initially and at most three
example images per record. Additional pages load through one owned scroll
sentinel. Switching filters or views cancels stale work, removes the prior
collection, and prevents late DOM updates.

Evidence images use fixed aspect-ratio frames, lazy decoding, bounded crops,
and explicit loading and failure states. Scope, parameter, composition and
render-setup cards share this geometry rather than inventing page-specific
image strips. Every recommendation distinguishes calculated candidates from
settings that were actually observed together.

The Playground keeps its compact evidence preview: one ranked group for
Character + Scene and one for Character + Scene + Outfit, with up to three
real example images per combination. These groups are derived from canonical
composition memberships; the broader Analytics composition view remains a
separate surface and does not replace them.

Each evidence group is a cyclic, arrow-controlled carousel. Native horizontal
scrollbars are hidden, but touch/trackpad scrolling remains available. Cards
adapt their width to one, two or three examples, and the image region consumes
the full bounded card height before textual evidence and the explicit handoff
action.

Generation controls preserve the useful V1 experiment workflow without
reviving its form orchestration: a submission may choose a fixed or randomized
ComfyUI seed, a bounded batch size, a Steps range and a CFG range/step. The
Application sweep policy expands those values into concrete sampler settings
before `GenerationService` is called; every resulting generation therefore
stores the exact seed, Steps and CFG values it used.

Top/Worst is the reference surface. Its cards show only rank, rating on the
1-10 scale, rating count and a small scope summary. Full technical metadata
belongs in the inspector.

## Responsive contract

- `>= 1800 px`: both side regions are pinned.
- `1367-1799 px`: compact rails, independently collapsible.
- `<= 1366 px` or coarse pointer: one side drawer at a time.
- The 1180 x 820 target is a functional iPad-landscape layout, not a separate
  mobile application.
- The center image or gallery must remain usable at every target width.

## Motion and accessibility

Motion is limited to state clarification: drawer movement, selection feedback
and short content transitions. All motion observes `prefers-reduced-motion`.
Keyboard focus is always visible. Dialogs trap focus and return it to their
opener. Selected, inferred, deleted and generation states use text or icons in
addition to color.

## Fidelity acceptance

Browser renders are compared with the accepted reference at 1920 x 1080 and
also checked at 3840 x 2160, 1366 x 1024 and 1180 x 820. The comparison covers
layout, typography, palette, panel geometry, image dominance, icon weight,
spacing, state feedback and responsive behavior.
