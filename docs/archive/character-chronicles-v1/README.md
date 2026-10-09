# Verworfener Character-Chronicles-Entwicklungsversuch — Archiv

**Dokumentrolle:** historischer Fundus · **Status:** ARCHIVED / REJECTED AS CURRENT BASELINE
**Quelle:** vollständig aus `docs/Concepts/` auf Repository-Revision `76d71f9c7723701664785aeaf07e0d7375a4f36a` übernommen · **Archivierung:** 2026-10-09

> [!CAUTION]
> **Dieses Archiv ist nicht die Produkt-Roadmap, nicht der aktuelle MVP und keine implementierte Zielarchitektur.** Der damalige Character-Chronicles-Entwicklungsversuch wurde verworfen. Begriffe in den Quelldokumenten wie „autoritativer Zielvertrag“, „DECIDED“, „Baseline abgeschlossen“, „MVP“, „Schema 57“ oder „implementiert“ sind **historische Selbstbezeichnungen**, keine Gültigkeitsaussagen über die jetzige ComfyReview-Codebasis.

## Zweck

Die Quellen bleiben für spätere Ideengewinnung, frühere Experimente und Entscheidungsherleitung auffindbar. **Originalinhalte bleiben nach einer vorangestellten Archivkennzeichnung erhalten**; insbesondere werden die alten Spielmechaniken nicht stillschweigend auf den neuen Card Battler übertragen.

**Aktuelle Quellen:** [Dokumentationsindex](../../README.md) · [Roadmap](../../ROADMAP.md) · [Entscheidungen](../../DECISIONS.md) · [Card-Battler-Ziel](../../CARD_BATTLER_TARGET.md).

## Ursprünglicher Langentwurf

- [Character Chat, VN und Prompt Recovery (historisches Gesamtkonzept)](historical-concept.md) – früher `docs/Concepts/POST_MVP_CHARACTER_CHAT_AND_PROMPT_RECOVERY.md`; enthält widersprechende und überholte Anweisungen, insbesondere einen damals als verbindlich bezeichneten Chronicle-MVP.

## Themenindex der ehemaligen Produktverträge

Die **24 Produktdateien** liegen weiterhin gemeinsam im Unterordner `product/`, sodass ihre ursprünglichen gegenseitigen relativen Bezüge erhalten bleiben. Diese thematische Sortierung ist ausschließlich ein **Leseindex**, keine Rangfolge oder Freigabe.

### Bildpipeline, Foundation und Lernen

- [baseline-and-entry-gates.md](product/baseline-and-entry-gates.md)
- [generation-profiles-and-trials.md](product/generation-profiles-and-trials.md)
- [rolling-m6-learning-loop.md](product/rolling-m6-learning-loop.md)
- [game-modes-and-guided-evidence.md](product/game-modes-and-guided-evidence.md)
- [visual-assets-quests-and-gates.md](product/visual-assets-quests-and-gates.md)

### Card Battler, Karten- und Deckmodell

- [card-art-composition-and-rendering.md](product/card-art-composition-and-rendering.md)
- [card-battler-board-and-combat-foundation.md](product/card-battler-board-and-combat-foundation.md)
- [card-battler-decks-turns-and-actions.md](product/card-battler-decks-turns-and-actions.md)
- [card-battler-effect-grammar-and-llm-authoring.md](product/card-battler-effect-grammar-and-llm-authoring.md)
- [card-battler-runtime-architecture.md](product/card-battler-runtime-architecture.md)
- [card-battler-zones-statuses-and-opcode-registry.md](product/card-battler-zones-statuses-and-opcode-registry.md)
- [card-crafting-and-playground-combination-lifecycle.md](product/card-crafting-and-playground-combination-lifecycle.md)
- [champion-slots-and-character-decks.md](product/champion-slots-and-character-decks.md)
- [deck-building-embeddings-and-llm-context.md](product/deck-building-embeddings-and-llm-context.md)

### Character, Story, Welt und Abschluss

- [story-cast-and-simulation.md](product/story-cast-and-simulation.md)
- [school-year-visual-portfolios-and-relationship-contexts.md](product/school-year-visual-portfolios-and-relationship-contexts.md)
- [vn-social-platform-and-card-loop-concept.md](product/vn-social-platform-and-card-loop-concept.md)
- [year-end-lora-and-new-game-plus.md](product/year-end-lora-and-new-game-plus.md)

### UI, Social-/VN-Screens und Systembetrieb

- [frontend-information-architecture.md](product/frontend-information-architecture.md)
- [network-first-vn-frontend-screen-map.md](product/network-first-vn-frontend-screen-map.md)
- [player-facing-terminology-and-voice.md](product/player-facing-terminology-and-voice.md)
- [llm-rag-and-recovery.md](product/llm-rag-and-recovery.md)
- [orchestration-guardian-and-monitoring.md](product/orchestration-guardian-and-monitoring.md)
- [target-architecture.md](product/target-architecture.md)

## Umgang mit historischen Links und Behauptungen

Einige aus dem verworfenen Quellbestand übernommene Links zeigen bereits auf damals verschobene oder inzwischen nicht mehr vorhandene Ordner, etwa `docs/post-mvp`, `docs/vnext-mvp`, `foundation`, `acceptance` oder `historical-reference-bootstrap-and-evaluation.md`. **Diese fehlenden Zielseiten werden nicht erfunden und nicht als aktuelle technische Referenzen rekonstruiert.** Die Verweise bleiben im erhaltenen Originaltext sichtbar; für aktuelle Projekte bitte die [dokumentierte Autorität](../../README.md#verbindlichkeit-und-vorrang) heranziehen.

Die automatische Linkprüfung kontrolliert deshalb **aktive** Markdown-Dateien, nicht die historischen Quellverweise in diesem Archiv. Querverweise zwischen direkt nebeneinanderliegenden archivierten Produktdateien können weiterhin als Lesehilfe dienen, ohne ihnen Verbindlichkeit zu verleihen.

## Wiederverwendung nur mit aktiver Entscheidung

1. Die konkrete Idee und ihren historischen Kontext benennen.
2. Prüfen, ob sie mit dem heutigen ComfyReview-Code und den aktuellen Phasenzielen vereinbar ist.
3. Offene Fragen/POCs im [Register](../../POC_REGISTER.md) erfassen.
4. Eine neue CRCC-Entscheidung treffen und einen **neuen aktiven Vertrag** erstellen.
5. Historische Dokumente historisch lassen; alte „DECIDED“-Zeilen nicht umetikettieren.

Für den Card Battler ist bereits ausschließlich der [beschränkte ComfyReview-Zielvertrag](../../CARD_BATTLER_TARGET.md) maßgeblich. Dessen ausstehende Deck-/Board-/Mechanik-Entscheidungen bleiben offen.
