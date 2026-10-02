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

The generated reference's Japanese claim, user avatar, settings control,
global search, grid/list toggle and ranking sort control are intentionally not
part of the product. Scope search remains available inside the Scope Navigator.

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
