# ComfyReview Card Battler Target — historical plan (2026-10-02)

> **ARCHIVED planning record (reclassified 2026-10-09).** This
> **predates** the Character Chronicles concept import and represents an
> earlier ComfyReview direction, not the currently agreed next milestone.
> Its original statements about approval, mandatory phases and reuse by
> Character Chronicles describe the **old plan**, not a confirmed restart
> architecture or schedule. The Card Battler is now **active POC work
> inside ComfyReview**, which is intended to evolve toward Character Chronicles.
> This archived seven-phase plan may inform experiments but cannot require
> them to follow its design. The [imported vision](../character-chronicles/README.md)
> includes assumptions from an **earlier discarded Chronicle approach**:
> those are separately reviewable. Current ComfyReview code:
> [pre-import baseline](../IMPLEMENTATION_AUDIT.md);
> [open decisions](../OPEN_DECISIONS.md).

Document role: approved post-refactor product and architecture target for a
functional Card Battler prototype implemented in ComfyReview before later reuse
in Character Chronicles.

Status: approved **playable-product target** (2026-10-02), **not** a
completed or accepted runtime feature. **Source recheck 2026-10-09:** real
Card Battler Python library/prototype code already exists (read-only model,
semantic mapping, deterministic mechanics, Trait development, visual-prompt
projection) with automated tests. However, no registered card collection,
crafting/deck/match API or player UI is implemented. This document preserves the **desired boundary at the time it was written**;
it is neither current Card-Battler-POC acceptance nor an instruction to
implement every phase as written. [Active POC](../pocs/card-battler.md).
See [ComfyReview code baseline](../IMPLEMENTATION_AUDIT.md) and
[open decisions](../OPEN_DECISIONS.md).

## 1. Purpose and delivery boundary

ComfyReview will become the first implementation and proving ground for the
Card Battler. Existing reviewed images provide the source material, but card
crafting, card presentation, deck construction and match simulation form their
own bounded product area. Character Chronicles may later reuse that proven
boundary and add its own narrative, Champion and social progression systems
around it.

This target deliberately does not make the Card Battler part of refactor
acceptance. Work begins only after the current refactor has reached its required
acceptance state, unless a later explicit planning decision changes that order.
The implemented content policy, stable identity, generation and output
quality, plus the tested *offline Card Battler model and algorithms*, are
preparatory foundations. They are **not a shipped Card Battler vertical slice**
without the explicit player command, persistent CardIdentity, UI and acceptance
tests required below.

The Character Chronicles design documents are the design source for this
target, not a runtime dependency. This document restates the subset that
belongs in ComfyReview and removes Character Chronicles-specific assumptions.

The reviewed source set covers its card-crafting and Playground-combination
lifecycle, image-card collection and deck distinction, card-art composition,
deck/turn/action rules, board and combat foundation, effect grammar and opcode
registry, and server-authoritative runtime architecture. Only the contracts
restated here are authoritative for ComfyReview.

The initial ComfyReview target includes:

- an explicit manual action that develops one eligible canonical image into a
  card;
- a card collection and a manual card-art composition flow;
- deterministic, versioned card rules and effects;
- battle-driven Rarity/Level progression, persistent Trait lineages and
  manually selected visual evolution of the same card;
- revisioned deck construction and readiness validation;
- a deterministic, server-authoritative PvE Card Battler vertical slice;
- a browser game surface that renders server-confirmed state;
- architecture that can later be reused by Character Chronicles without
  importing ComfyReview review routes or persistence details.

The initial target excludes:

- automatic card creation from a rating, ranking, Arena result or Curation
  assignment;
- Character Chronicles Keep, Favorite, Champion, booster, cup, Visual Circuit,
  story, VN, social or relationship progression triggers;
- PvP, matchmaking and real-time multiplayer transport;
- LLM-authored executable rules, numbers or match decisions;
- a requirement to reproduce the Character Chronicles 40-card ruleset before
  the smaller ComfyReview prototype has been validated;
- implementation during the current refactor acceptance sequence.

## 2. Core domain model

The first slice uses the following mental model:

```text
Canonical Image
  -> explicit Develop as Card command
  -> CardIdentity
       |- CardMemoryOriginRevision
       |- ImageBrandingRevision
       |- CardRulesRevision
       |- CardDevelopmentEvent* -> CardBattleExperienceProjection
       |- CardEvolutionRevision*
       `- CardArtCompositionRevision -> CardFaceAssetRevision
  -> Card Collection
  -> revisioned Deck
  -> frozen MatchSnapshot
```

`CardIdentity` is the stable identity of a card. The source image path is not
identity. `image_uid` identifies the canonical source image and remains a
reference on the image-branding revision.

In the initial ComfyReview contract:

- one source image can create at most one personal `CardIdentity`;
- repeating the same develop command is idempotent and returns the existing
  card rather than creating a duplicate;
- the source PNG is not copied, cropped, renamed or mutated to create a card;
- changing rules or presentation creates a new revision of the same card;
- development, battle experience and visual evolution remain attached to that
  same identity rather than producing stronger duplicate cards;
- a card is not a review rating, an Arena result or a Curation assignment;
- card history remains addressable even when the current card is unavailable.

Rules, image binding and presentation are independent revision chains:

- `CardRulesRevision` owns card statistics, archetype, traits and executable
  effects;
- `ImageBrandingRevision` binds the card to one canonical image revision and
  its permitted provenance;
- `CardArtCompositionRevision` owns frame, normalized crop focus, zoom and the
  reproducible presentation recipe;
- `CardFaceAssetRevision` is a rebuildable presentation asset and never a new
  canonical image or card.

No operation may silently mutate another chain. Reframing a card does not
reroll its rules, and a rules revision does not change its source image.

## 3. Manual card development

Card development starts only from an explicit user command on an eligible
image, such as `Develop as Card`. The command is never inferred from score,
rank, frequency, prompt content or Arena performance.

The application service validates the image by stable UID, evaluates current
card eligibility and atomically materializes or resolves:

1. the stable `CardIdentity`;
2. its initial `ImageBrandingRevision`;
3. an initial deterministic `CardRulesRevision`, once deterministic crafting
   is part of the delivered phase;
4. an immutable `CardMemoryOriginRevision` containing the eligible source
   image revision and first materialized card state;
5. the collection projection and art-composition state.

Once deterministic crafting is available, the manual image-to-card action is
the first development step. It materializes the image card as `Common Level 1`
and creates its first deterministic Trait. ComfyReview has no Keep/Favorite
shortcut to a higher starting rarity.

The first collection slice may show a clearly marked pending card before final
art composition is confirmed. Pending presentation must not create a second
identity or block later completion.

Deleting or otherwise making the canonical source image unavailable suspends
the active image branding and card eligibility without erasing card history.
Restoring an otherwise eligible source image may restore availability through
an explicit projection rule. Unlike the Character Chronicles base-deck model,
the initial ComfyReview target does not silently replace a deleted image card
with a blank standard card. A match that already started keeps its frozen
snapshot unchanged.

## 4. Card-art composition and rendering

The manual editor has one dominant task: place the source image inside a
versioned card frame. It supports pan, zoom, reset, cancel and confirm. The
persisted transform is resolution-independent:

```text
source_image_uid
source_image_revision
frame_template_revision_id
focus_x = 0.0 .. 1.0
focus_y = 0.0 .. 1.0
zoom = 1.0 .. policy maximum
rotation_degrees = 0 in the first version
composition_policy_revision
```

`zoom = 1.0` is the minimum cover fit that fills the complete art window.
Transforms are clamped so no accepted composition exposes missing source
pixels. Free rotation, perspective transforms, non-uniform scaling and
destructive source-image cropping are outside the first version.

The browser owns only the interactive preview. A dedicated renderer adapter
validates the source revision, frame revision and normalized transform, renders
the authoritative face asset and records a render receipt containing all input
revisions, renderer revision and output hash. Retrying identical semantic
inputs is idempotent.

Frame templates, render profiles and outputs are versioned. Drafts are
resumable and use optimistic revision checks. Confirmed composition revisions
and render receipts are append-only. Accessible mouse, touch and keyboard
controls are required before this phase is accepted.

## 5. Deterministic card rules

The first playable cards use a fixed, server-owned rule grammar. Mechanics are
selected from versioned archetypes, traits and effect opcodes; they are not
generated as executable natural language.

Every initial rules materialization binds at least:

```text
card_identity
craft_seed
ruleset_revision
balance_policy_revision
effect_registry_revision
card_rules_revision
```

The same eligible inputs, craft seed and rule revisions produce the same
semantic card result. The materialized result is persisted, so later balance
or registry changes never reinterpret an existing historical card or match.
Randomness is obtained only from an explicit persisted seed and a versioned
algorithm; language-runtime hashes, row order and current time are not valid
sources of deterministic behaviour.

The server owns statistics, targets, costs, legal timing and effect execution.
A later LLM integration may phrase a title, flavour text or explanation from
already materialized facts, but it may not invent numbers, opcodes, targets,
legality or match actions.

The first ruleset should be intentionally small. Its exact card statistics,
deck size, zones and opcode list are calibration decisions made before that
phase starts, not reasons to weaken the identity, revision or determinism
contracts now.

## 6. Card development and battle evolution

Card development is part of the ComfyReview prototype, not a deferred
Character Chronicles-only feature. It is a persistent progression path of the
same CardIdentity and must be implemented and playtested under the same
architecture, determinism, migration and quality standards as the Battler.

### Development ladder and Trait lineage

The prototype adopts the Character Chronicles development ladder:

```text
Common -> Uncommon -> Rare -> Super -> Ultra -> Legendary
```

`Common` through `Ultra` each contain `Level 1`, `Level 2` and `Level 3`.
After Level 3, the next valid development step reaches Level 1 of the next
rarity. A card can never be actively downgraded to an earlier rules revision.

Every development step consumes a versioned mechanical budget and performs
exactly one primary Trait action:

1. add the first Trait when none exists;
2. improve an existing Trait in a registered dimension; or
3. add a new compatible Trait when the current rarity cap permits it.

The initial caps are:

| Rarity | Maximum Traits |
| --- | ---: |
| Common | 1 |
| Uncommon | 2 |
| Rare | 2 |
| Super | 3 |
| Ultra | 3 |
| Legendary | 3 |

The first Trait creates a persistent `TraitLineage` with a mechanical anchor
and versioned compatibility policy. Later Traits and upgrades must support that
lineage through compatible trigger, target, position, cost or payoff semantics.
Reaching the cap requires an upgrade to an existing Trait rather than an
unrelated additional ability. A development step never rerolls the card's
identity, source image, initial combat profile or existing lineage.

Higher rarity and level may increase values, flexibility and effect strength,
but also their versioned play or deck-building requirements. Progression must
therefore preserve a useful deck curve rather than making every highest-rarity
card universally optimal.

### Battle experience boundary

The match reducer never mutates or promotes a card. Only a confirmed
`match_completed` may emit one deduplicated `CardBattleUsageFact` per used
CardIdentity from the append-only match events. Relevant facts may include
legal play, resolved Trait use, attack or defence contribution, decisive
events and the versioned encounter classification.

An idempotent `card_crafting` consumer evaluates those facts under explicit
experience and anti-farm policy revisions and materializes accepted
`CardBattleExperienceEvent`s. Replay, HTTP retry, duplicate outbox delivery or
reprocessing cannot award experience twice. No-op use, immediate concession,
repeated scripted opponents and other declared farm patterns are rejected or
capped. A win by itself is not an experience threshold.

Accepted events build a reproducible `CardBattleExperienceProjection` and a
data-minimal digest. Reaching a versioned threshold creates
`card_development_ready`; it does not itself change card rules. A separate,
idempotent development command consumes that readiness exactly once and
materializes the next deterministic `CardRulesRevision`. The new revision is
available only to matches started afterwards.

### Visual evolution

The original `CardMemoryOriginRevision` is immutable. A post-origin promotion
may additionally open a separate visual evolution trial:

```text
immutable CardMemoryOriginRevision
  -> accepted CardBattleExperienceEvent*
  -> reproducible CardBattleExperienceDigest
  -> card_development_ready
  -> deterministic next CardRulesRevision
  -> four CardEvolutionImageCandidates
  -> manual accept, preserve-current or reject-all decision
  -> optional active CardEvolutionRevision of the same CardIdentity
```

Candidate generation is a ComfyUI provider workflow over an already compiled,
versioned recipe. It may use the safe, bounded experience digest to express
the card's established career visually, but may not invent mechanics, match
facts or canonical events. No SQLite write transaction remains open while
ComfyUI runs. Submission, polling, output collection and ambiguous-timeout
recovery follow the existing provider boundaries.

Accepting one candidate creates a new immutable `CardEvolutionRevision`, new
image-branding and art-composition inputs, and a new active presentation of the
same card. The origin and intermediate forms remain historically visible, but
only the highest accepted form is actively playable. Preserving the current
form or rejecting all candidates leaves the previous presentation active and
keeps the earned visual evolution pending for a later retry. Human choice
selects presentation only; it does not choose or increase mechanical strength.

Evolution imagery is card mythology, not evidence that the depicted event
occurred. It does not rewrite source generation provenance, ratings, prompt
facts or the immutable memory origin. A generated candidate is not a second
CardIdentity and is not added to the ordinary review loop as an unrelated
canonical source image. It receives a stable candidate/asset identity and
complete generation, workflow and content-policy provenance inside the
evolution trial. Only eligible collected outputs may be shown for selection.

### Legendary boundary in the ComfyReview prototype

Character Chronicles requires both a long anti-farm Battle Lineage and a
separate visual competition history for `Legendary`. That champion/booster/cup
system is intentionally outside ComfyReview. The prototype therefore develops
and tests the sequential ladder through `Ultra Level 3`, but keeps the
Legendary transition locked. Battle experience alone cannot grant it.

Unlocking Legendary in ComfyReview requires a later explicit product contract
for an equivalent independent proof or a decision to keep final Legendary
materialization exclusive to Character Chronicles. Testing may exercise the
locked gate with deterministic fixtures; production code must not bypass it.

## 7. Collection, playable pool and decks

These concepts remain distinct:

- **Card collection:** every current and historical card owned by the local
  ComfyReview profile, including pending or unavailable cards;
- **Playable pool:** the current subset that satisfies image, content, rules
  and availability policies;
- **Deck:** a named, revisioned selection of unique playable CardIdentities for
  a specific ruleset.

The first UI therefore uses `Card Collection` or `Card Workshop` for the area
that displays all manually developed cards. It uses `Deck` only after the user
can deliberately add and remove cards from a concrete deck.

Deck readiness is validated on the server against a versioned rules profile.
The prototype may use fewer than forty cards, but the chosen size, duplicate
policy and required card state must be explicit rather than UI conventions.
Saving a deck creates a new deck revision; it does not copy or fork its cards.

## 8. Functional Battler vertical slice

The first game mode is deterministic local PvE. The server is the only rules
authority:

- commands are validated against the current match revision and legal-action
  projection;
- an accepted command produces domain events and the next confirmed state;
- the same rules, decks, card revisions, opponent profile, seed and command
  sequence produce the same semantic event stream and state hash;
- bounded advancement stops at the next player decision or terminal result;
- opponent actions pass through the same legal-action and reducer boundary as
  player actions;
- failures are normalized and never repaired by browser-side rule guesses.

Match start freezes a `MatchSnapshot` containing both deck revisions, every
used CardIdentity and CardRulesRevision, presentation revisions used for the
match, the rules and registry revisions, opponent policy revision and RNG
seed. Later card development, reframing, image deletion or balance changes do
not rewrite a running or completed match.

HTTP request/response commands are sufficient for the initial local
singleplayer slice. WebSocket, SSE, PvP and matchmaking are not prerequisites.

The browser may use a game renderer for board motion and a DOM layer for text,
dialogs and accessible controls. Both render a viewer-safe server projection.
Neither owns match state, determines legal actions or executes card effects.

After `match_completed`, the Battler may publish deduplicated usage facts for
the development pipeline described above. It may not calculate experience,
advance Rarity or Level, choose a Trait action, generate evolution art or
activate a new card revision.

## 9. Content-policy and image-eligibility boundary

The global ComfyReview content policy applies to every Card Battler read and
mutation. A disabled image cannot be reintroduced through collection, card,
deck or match endpoints by supplying a known stable ID.

Character Chronicles keeps adult-content pools separate from battler cards.
Whether ComfyReview permanently adopts that stricter boundary for enabled
`sexy`, `lewd`, `nude` and `explicit` images remains an explicit product and
safety decision. Until it is resolved and documented, implementation fails
closed: only images classified as `standard` may create or actively brand a
card. Enabling another level for Review or Generation must not implicitly make
that level Card Battler eligible.

Eligibility is normalized domain policy over canonical facts. It is not a CSS
filter or repeated prompt keyword scan. Existing cards whose source becomes
disabled or is reclassified outside the eligible level retain auditable
history but leave the active playable pool. Frozen matches remain unchanged.

This application policy does not by itself settle direct filesystem URL access;
that remains a separate output-delivery and security decision.

## 10. Architecture and ownership

The intended dependency direction is:

```text
card_crafting -> card_collection -> deck -> card_battler
        |                |                     |
        `-------- typed application ports -----'
                         |
          repositories and renderer adapters
```

- `card_crafting` owns eligibility orchestration, idempotent card creation,
  deterministic rule materialization, development events, experience policy,
  Trait lineage, evolution activation and composition confirmation.
- `card_collection` owns current and historical card projections, presentation
  status, development history and playable-pool projection.
- `deck` owns named deck revisions and readiness validation.
- `card_battler` owns match snapshots, legal actions, deterministic reduction,
  PvE policy, events, results, replay facts and post-match usage facts, but not
  experience or promotion decisions.
- HTTP routes translate requests and responses only.
- repositories own all SQL and target the one canonical writable SQLite
  database.
- renderer and filesystem adapters own card-face file IO.
- browser modules use the shared frontend API boundary and own disposal of
  listeners, timers and in-flight requests.

No SQLite write transaction remains open while rendering a card face or
waiting on another external boundary. Mutations that materialize one domain
decision are atomic. Output paths are attributes, never card or asset identity.

ComfyReview-specific review services are upstream sources of eligible image
identity only. The reusable card domain must not import routes, Jinja
templates, concrete SQLite paths, ComfyUI clients or Character Chronicles
gameplay modules.

## 11. Persistence and recovery

Card Battler persistence belongs in the canonical database through explicit,
versioned schema migrations. Normal startup validates the supported schema and
never silently upgrades an existing database. Every migration creates and
validates a backup and a new migration output according to the repository
rules.

The minimum conceptual persistence covers:

- card identities and image-branding revisions;
- deterministic craft receipts and card-rules revisions;
- immutable memory origins, card-development events, Trait lineages,
  battle-usage facts, experience events, digests and rebuildable projections;
- evolution trials, generated candidates, player decisions and immutable
  evolution revisions;
- frame-template, composition-draft and confirmed composition revisions;
- face-asset revisions and render receipts;
- collection/playability projections that are rebuildable from canonical
  facts;
- deck identities and deck revisions;
- match heads, frozen snapshots, commands, domain events and results.

Large image, prompt or rating payloads are not duplicated per card or event.
Stable foreign keys bind canonical facts. Derived presentation assets and
projections are explicitly marked rebuildable. Retried commands use stable
command or idempotency keys and cannot create duplicate cards, confirmed
compositions, deck revisions or match transitions.

## Verified groundwork versus delivery phases

The offline foundations are implemented in
[`comfyreview/application/card_battler_*`](../../comfyreview/application),
[`comfyreview/domain/card_battler`](../../comfyreview/domain/card_battler),
and the [read-only external model adapter](../../comfyreview/repositories/sqlite/card_battler_model_resource.py);
the [existing card tests](../../tests/test_card_battler_development_golden_path.py)
exercise deterministic behavior. The model database itself is **not
committed**, and these algorithms are **not** a playable end-to-end user flow.
For individual deliverables see [historical status and open decisions](../OPEN_DECISIONS.md).

## 12. Binding implementation order

The following order captures the approved product progression. It is separate
from, and begins after, the active refactor sequence.

### Phase 1: manual card development and collection

- add explicit `Develop as Card` eligibility and command behaviour;
- create one stable CardIdentity per eligible source image idempotently;
- add the card collection/workshop projection;
- add the manual frame, pan and zoom composition flow plus authoritative
  rendering;
- define deletion, restoration, pending-art and unavailable-card behaviour;
- do not add combat or pretend the collection is already a deck.

### Phase 2: deterministic card functions

- introduce the small versioned ruleset, archetypes and opcode registry;
- assign and persist rules from an explicit craft seed and policy revisions;
- establish Common Level 1, the development ladder, budgets, Trait caps and
  persistent TraitLineage rules even before match experience can advance them;
- expose human-readable deterministic card functions in collection views;
- keep LLMs outside mechanics and verify replayable materialization.

### Phase 3: deck construction

- add named, revisioned decks over existing CardIdentities;
- add server-side playable-pool and deck-readiness validation;
- select and document the prototype deck size and duplicate policy;
- do not copy cards into decks or encode readiness only in the UI.

### Phase 4: functional PvE Battler

- implement the deterministic server-side match aggregate and reducer;
- freeze deck, rule, card and presentation revisions at match start;
- add the smallest complete set of zones, turns, legal actions, effects,
  opponent decisions, victory conditions and replay facts;
- test success, illegal commands, stale revisions, step budgets, recovery and
  completed-match immutability.

### Phase 5: battle-driven card development and evolution

- emit deduplicated post-match usage facts without mutating match snapshots;
- implement versioned experience and anti-farm policies plus rebuildable
  experience projections;
- consume a readiness threshold exactly once into the next deterministic
  CardRulesRevision and compatible Trait action;
- add the four-candidate visual evolution trial, preserve/reject behaviour and
  immutable MemoryOrigin/Evolution history;
- exercise the full Common-to-Ultra path and enforce the locked Legendary gate;
- verify that all changes affect only future matches.

### Phase 6: game and development interface

- add the interactive board, hand, action prompts and result presentation;
- show current Rarity, Level, Trait lineage, experience progress, pending
  development and historical card forms without presenting projections as
  editable authority;
- add the resumable evolution-candidate review and explicit accept,
  preserve-current and reject-all decisions;
- keep text-heavy and accessibility-sensitive controls in the DOM;
- render only confirmed server projections and map input to semantic commands;
- complete keyboard, pointer, touch, small-viewport and reduced-motion paths.

### Phase 7: hardening and Character Chronicles reuse

- run the complete quality, architecture, determinism and browser gates;
- document the stable reusable domain and application ports;
- remove accidental dependencies on ComfyReview presentation or review
  orchestration;
- only then reuse the proven Card Battler boundary in Character Chronicles,
  where narrative, Champion and non-card progression systems remain separate
  adapters and extensions.

Each phase is a separately accepted vertical slice. No phase is complete until
its behaviour tests, failure and rollback tests, callable manifest, formatting,
linting, typing, architecture checks and full shared quality gate pass.

## 13. Acceptance invariants

1. Repeating manual development for the same source image never creates a
   second CardIdentity.
2. Card rules, image branding and art composition can be revisioned
   independently without silent cross-mutation.
3. Identical versioned craft inputs produce the same semantic rules result.
4. Every accepted development step advances exactly once along the versioned
   ladder and performs exactly one legal Trait action within its cap.
5. Match completion, retry, replay and duplicate delivery never award the same
   CardBattleExperience twice.
6. The Match reducer can emit usage facts but cannot promote a card; a new
   revision applies only to future MatchSnapshots.
7. Accepting or rejecting evolution art never changes the already materialized
   mechanical development result.
8. MemoryOrigin and historical evolution forms remain immutable; at most one
   highest accepted form is active.
9. Battle experience alone cannot bypass the ComfyReview Legendary lock.
10. Natural-language output is never executable rule authority.
11. The browser cannot submit or display a disabled or otherwise ineligible
   image as an active card by known UID.
12. Decks reference CardIdentities and revisions; they do not duplicate cards.
13. Illegal, stale or repeated commands do not partially mutate a deck or match.
14. Equal frozen match inputs and command sequences produce equal semantic
   events and state hashes.
15. A running match remains unchanged by later card, image, frame, deck or
   balance revisions.
16. Card-face rendering is reproducible from recorded revisions and receipts;
    source images remain unchanged.
17. SQL, filesystem IO, HTTP translation, business rules and browser rendering
    remain in their assigned boundaries.
18. Documentation always distinguishes target, migrated and live behaviour.

## 14. Deferred calibration decisions

The target architecture does not yet fix:

- the prototype deck size and opening-hand size;
- exact board zones, turn phases and victory totals;
- the first archetype, statistic and opcode catalog;
- exact development budgets, experience thresholds, anti-farm caps and the
  visual evolution generation recipe;
- final frame artwork, card-face dimensions and encoding profile;
- whether deterministic crafting uses only a persisted random seed or also
  selected normalized, non-sensitive generation facts;
- whether enabled non-`standard` content remains permanently excluded from
  Card Battler eligibility, as it is in the Character Chronicles design;
- whether Legendary remains exclusive to Character Chronicles or receives an
  independent ComfyReview proof contract;
- the visual engine used for the later board.

These decisions must be made and versioned before their implementation phase.
They do not reopen the stable identity, explicit revision, server authority,
content eligibility or implementation-order contracts above.
