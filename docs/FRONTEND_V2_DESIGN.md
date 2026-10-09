# ComfyReview Frontend V2 Design Contract

Status: accepted implementation reference on `refactor/review-boundary`,
2026-10-01.

## Product frame

**Scope boundary:** this is the accepted **current ComfyReview tool UI**
design reference, not the later Character Chronicles Timeline, social/chat,
story or VN interface. Future UX requires phase-specific decisions under
[ROADMAP.md](ROADMAP.md) and [DECISIONS.md](DECISIONS.md); the archived
Character Chronicles screen maps are not automatically authoritative.

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

The surface contains General, Content levels, LoRA status, Review, Curation,
ComfyUI, and Storage and database sections. General preferences, content
levels and LoRA classifications are live canonical data. Catalog is the only
LoRA editor; Settings shows availability/unclassified diagnostics and links to
it rather than owning a second form.
Environment-derived infrastructure settings are read-only, name their
controlling environment variable, and state when a restart is required. The
browser never writes `.env`.

Generation profiles are not an active UI or runtime concept. The Generator
owns checkpoint, sampler, scheduler, Steps, CFG, Denoise, Batch, classified
LoRAs, format and resolution class directly. Content levels begin with
mandatory Standard and are enforced server-side across all image collections;
the browser only edits the canonical preference. Review and Curation settings
are UI/session defaults only and do not change review-event or assignment
semantics.

The Review preference is labelled “Unbewertete Bilder priorisieren”. It does
not hide rated images: new unrated images appear first, followed by the
longest-waiting rated image. The obsolete maximum-attempt input is not rendered
or sent. Generation details poll only canonical server state; for
`reconciliation_required` they show the normalized reason and one explicit
“Auftrag / Output abgleichen” action. The browser does not own a generation
queue or filesystem recovery policy.

## Collection and evidence contract

Analytics collections render at most 24 records initially. Example evidence
uses one large cyclic carousel per card instead of shrinking several images
beside one another. Additional pages load through one owned scroll sentinel.
Switching filters or views cancels stale work, removes the prior collection,
and prevents late DOM updates.

Overview metrics, Scope evidence and Render evidence use one lifecycle-owned
cyclic card-rail component. Tablet widths from 768 through 1366 CSS pixels show
exactly three equally wide cards. Cards preserve their own natural height,
media is never cropped, and outer rail gestures are isolated from each card's
inner evidence carousel. Playground applies the same rail behavior to one
Top-2 and one Top-3 row per canonical character.

`EvidenceCarousel` owns arrows, pointer swipes, horizontal wheel input,
position display, image failures and listener disposal. Scope, parameter,
composition, Draft and catalog evidence reuse it together with the existing
full-size `ImageViewer`. Every recommendation distinguishes calculated
candidates from settings that were actually observed together.

The Playground keeps one ranked group for Character + Scene and one for
Character + Scene + Outfit. Each combination card uses one large cyclic
`EvidenceCarousel` for up to three real examples instead of shrinking images
beside one another. These groups are derived from canonical composition
memberships; the broader Analytics composition view remains a separate surface
and does not replace them.

`/playground` is this evidence overview. `/playground/generator` owns the
authoring flow, while `/generations` owns generation history. A handoff carries
stable component or revision IDs and does not create a draft by itself.

Each evidence group is a cyclic, arrow-controlled outer carousel. Inner image
gestures are isolated so one swipe never moves both layers. Native horizontal
scrollbars are hidden, but touch/trackpad scrolling remains available.

True image-card collections share one `media-card-grid` contract: exactly three
equal-width, top-aligned columns at 1180×820 and 820×1180, two below the tablet
breakpoint and one on very narrow screens. Desktop grids may add columns.
Images always retain their natural ratio (`width: 100%; height: auto`) without
`cover` cropping, so card heights may differ. Top/Worst, Analytics and the
Playground overview use this contract; Generator/Draft/Catalog evidence reuse
the same uncropped media rule in their specialized one- or two-card layouts.

Generation controls preserve the useful V1 experiment workflow without
reviving its form orchestration: a submission may choose one fixed or
randomized seed, a bounded batch size, a Steps range and a CFG range/step. The
server materializes a random seed before draft creation and uses that same
value for component selection and the base sampler. The Application sweep
policy expands those values into concrete sampler settings before
`GenerationService` is called; every resulting generation therefore stores the
exact seed, Steps and CFG values it used.

The Generator divides controls into Render/Sampler, Output and Runtime groups.
Steps and CFG use a single track with two accessible handles; their numeric
range is read-only text, and CFG step appears only for a real sweep. A
`RenderGuidancePanel` exposes two independent switches—Gesichtet/Rechnerisch
and Gesamtsetup/Einzelwerte. Applying guidance changes only the six render
fields, collapses Steps/CFG to point values, invalidates the reviewed draft and
requests a fresh server assessment. Color is relative within a parameter/list
and is always accompanied by score, image count, review count, provenance and
confidence text.

Analytics uses the same four-mode matrix. Every source action delegates a
typed handoff to `GeneratorHandoffNavigator` and navigates directly to the
Generator. `GeneratorHandoffApplier` loads, projects and applies the intent
atomically to the visible controls, then removes the handoff parameters with
`history.replaceState`. There is no tab-local staging store, tray or duplicate
toast owner.

Drafts are server-identified and group positive and negative atoms by their
canonical component order. Atom edits are draft overrides only; preview and
submission use the same server renderer. Two evidence cards independently rank
prompt similarity and sampler similarity, prefer matching geometry, and share
the canonical content-visibility policy.

Top/Worst is the reference surface. It includes every live image with at least
one rating and labels its result count accordingly; Analytics/Arena evidence
thresholds do not silently reduce this gallery. Cards show only rank, rating on
the 1-10 scale, rating count and a small scope summary. Full technical metadata
belongs in the inspector. Settings renders detected LoRAs without a stored
classification as `Nicht eingestuft` instead of visually defaulting them to
Standard.

All image-bearing surfaces share `ImageGeneratorActions`. A compact card menu
and prominent inspector buttons send Prompt-Setup and Render-Setup separately
through the same navigator. Evidence carousels therefore inherit the same
wording and direct-navigation behavior in Analytics, Catalog, Playground and
Draft as Top/Worst, Review, Arena and generation details. A failed handoff
leaves the previous Generator controls untouched and reports the error on the
target page.

## Responsive contract

- `>= 1800 px`: both side regions are pinned.
- `1367-1799 px`: compact rails, independently collapsible.
- `<= 1366 px` or coarse pointer: one side drawer at a time.
- The 1180 x 820 target is a functional iPad-landscape layout, not a separate
  mobile application.
- Overlay inspectors close through their visible close control, a repeated tap
  on the selected image, Escape, or a tap in the main surface outside the
  inspector. Inspector interactions do not dismiss the drawer, whose content
  owns viewport-bounded vertical touch scrolling.
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
