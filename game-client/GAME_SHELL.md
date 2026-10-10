# Game Shell v0 – room, smartphone, dynamic avatar

**Status:** Cocos scripts and headless navigation tests prepared; no genuine
Cocos Creator or FairyGUI integration has yet run. This is a _presentation
smoke_, not a new game mechanic or a Character Chronicles world-state model.

## Goal

Use Cocos Creator 3.8's **visual editor** to assemble a fixed personal room
and a phone overlay. The screen layout, positions, fonts, art, animation clips
and hit areas belong in the editor; TypeScript only handles UI navigation and
reuses the existing canonical image-preview component for a live avatar.

This avoids creating an unverified, hand-authored Cocos scene/prefab/meta file.
It deliberately **does not depend on FairyGUI** until Community integration has
passed a separate compatibility smoke. Creating the phone with Cocos UI first
is a reversible test, not a permanent decision against FairyGUI.

## Prerequisites

- A **genuine editor-created Cocos Creator 3.8.x Empty (2D) project** in
  `game-client/cocos` (see [SETUP.md](SETUP.md)).
- A local ComfyReview FastAPI instance only for the live avatar test.
- A real canonical `image_uid` from Studio. No player/contact API exists yet.
- No paid assets. Use temporary shapes, built-in UI, or approved artwork.

After Cocos creates the project, run `python game-client/scripts/install_starter.py`
from the repository root to install the TypeScript sources. Let the editor
import/generate `.meta` files.

## Build the scene using the Cocos visual editor

Create a **2D scene** named `GameShellSmoke`. Suggested hierarchy (names are
recommendations, not serialized contracts):

```text
Canvas
  RoomRoot                         [static placeholder room or approved art]
    PhoneHotspot                    [Button with click event]
  PhoneOverlay                      [Node, initially inactive]
    PhoneBackground                 [UI Sprite / 9-slice]
    CloseButton                     [Button]
    TabBar
      TimelineButton                 [Button]
      MessagesButton                 [Button]
      CardsButton                    [Button]
    TimelinePanel                   [Node]
    MessagesPanel                   [Node]
      DemoAvatar                    [Sprite + CanonicalImagePreview]
      DemoMessage                   [Label with SAMPLE TEXT, no LLM]
    CardsPanel                      [Node]
  GameShell                         [Node + GameShellController]
```

Both the room and phone elements can use editor-authored layouts and
animations. The root Canvas should remain responsible for UI resolution and
camera. Avoid reparenting dynamic assets at runtime solely for this smoke.

### Inspector connections

1. On `GameShellController` assign `RoomRoot`, `PhoneOverlay`, the three panel
   nodes, and optionally a small `viewStatusLabel`.
2. Assign `DemoAvatar` to `avatarPreviewNode` (the node with the
   `CanonicalImagePreview` component).
3. On the image-preview component assign its `targetSprite` and an optional
   status label. Leave its `imageUid` blank: the shell controller provides the
   UID **only when the messages tab is visible**.
4. Set the controller's `demoAvatarImageUid` to a real UID from ComfyReview.
5. Connect the `PhoneHotspot` Button Click Event to `GameShellController.openPhone`.
6. Connect `CloseButton` to `closePhone`, and the three tab buttons to
   `showTimeline`, `showMessages`, and `showCards`.
7. Save the scene and use the Web Desktop build plus the local proxy described
   in [SETUP.md](SETUP.md) for an actual API/texture smoke.

When the player closes the phone or changes away from Messages, the
preview component clears its owned image frame. Returning to Messages
loads it again. **This is demonstration behavior, not an image cache policy.**

## What the demo proves – and does not

It can prove, **after running inside Cocos**:

- The room is a persistent static scene while the phone opens on top.
- Buttons and tabs can switch game UI without webpage navigation.
- A runtime image URL from ComfyReview fills an editor-created UI Sprite.
- Closing the phone does not delete or modify any backend data.

It cannot prove a complete world hub, actual character/social identity,
conversation persistence, an LLM stream, card collection, game-save authority,
FairyGUI compatibility, or a shippable native build. Those interfaces have no
verified production APIs in the current ComfyReview code.

## Success criteria and owner acceptance

- [ ] Real Cocos Creator 3.8 editor has opened this project.
- [ ] Scene and generated metadata are saved by the Cocos editor.
- [ ] Room, phone open/close and three tabs work with mouse input.
- [ ] Current canonical image loads as a demo avatar (or shows clear error).
- [ ] Back/close hides the phone while the room stays visible.
- [ ] Repeat open/close and avatar reload do not crash or leak resources.
- [ ] Owner approves appearance and interaction in a running build.

Unit tests under `game-client/tests/game-shell-state.test.mjs` validate only
the presentation state transitions **without** claiming engine acceptance.
