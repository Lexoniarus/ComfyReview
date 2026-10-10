# Character Chronicles – Cocos Creator 3.8 smoke setup

**Status: code prepared, editor/import/native runtime not yet executed.**

This directory deliberately does **not** contain a fabricated Cocos scene,
prefab or `package.json`. Those belong to the real Cocos Creator editor.

## First editor setup (on your Windows or macOS workstation)

1. Check out `feature/character-chronicles-game-client` locally.
2. Install **Cocos Creator 3.8.x** through Cocos Dashboard.
3. In Dashboard choose **New → Empty (2D)** and set the project directory to
   `<repo>/game-client/cocos`. Create and open the project. This directory
   should now contain `package.json`, `assets/`, and editor-generated config.
4. With Cocos closed (or before first import), run from the repo root:

   ```powershell
   python game-client/scripts/install_starter.py
   ```

5. Reopen the project in Cocos so it imports the scripts and generates `.meta`
   files. **Commit the actual editor-generated `.meta`, scenes and settings**;
   never commit `cocos/library`, `cocos/local`, `cocos/temp`, or `cocos/build`.

## Create the smoke-test scene in the visual editor

1. Create a new 2D scene called `ImagePreviewSmoke`.
2. Add a canvas-backed `Sprite` node with a placeholder background and an
   optional `Label` for loading status. Only freely licensed/synthetic test
   assets should be committed.
3. Add `CanonicalImagePreview` as a component to a node in the scene.
4. Link its `targetSprite` and `statusLabel` fields via drag-and-drop in the
   Inspector. Set `imageUid` to a **real, visible** `image_uid` returned from
   the Studio/API. Leave `apiBaseUrl` empty for the same-origin Web smoke.
5. Add a Cocos `Button`; in Click Events select the component and its `reload`
   method. This is a genuine user interaction that reloads the image.
6. Save the scene and make it the startup scene in Project → Build.

The component retrieves `GET /api/v2/images/{image_uid}` and uses the response's
existing `image_url` (`/files/...`) for remote loading. No new Python endpoint,
database schema, ComfyUI call, or manually generated Cocos scene data is needed.

## Important: local Web CORS

The existing FastAPI server defaults to `http://127.0.0.1:8000` and does not
necessarily allow cross-origin Web build traffic. Browsers will block a
Cocos preview served from another origin when it attempts to load ComfyReview
PNG textures. **Do not turn off browser security** as a workaround.

For a connected Web smoke, build the Cocos project for **Web Desktop** through
Project → Build. In a second terminal, from the repository root run:

```powershell
python game-client/scripts/dev_proxy.py --build "game-client/cocos/build/<actual-web-build-folder>"
```

Replace `<actual-web-build-folder>` with the real directory containing the
editor-generated `index.html`; Cocos output paths depend on the build task.
Then open `http://127.0.0.1:8787/`. The proxy serves static Cocos files and
forwards only `/api/v2/` and `/files/` to `http://127.0.0.1:8000`.
It binds **only** to localhost, needs no backend changes, and is NOT suitable
for public deployment or remote devices. It is not an authentication layer.
Do **not** turn off browser security as a workaround.

A native Cocos build uses different HTTP/asset platform behavior; verify it
separately before declaring native integration accepted.

## Quality checks available without the Editor

```bash
node --experimental-strip-types --test game-client/tests/image-api.test.mjs
python -m unittest discover -s game-client/tests -p 'test_*.py'
tsc -p game-client/tsconfig.contract.json
```

The pure API client and installer can be validated headlessly. The
Cocos-dependent `CanonicalImagePreview.ts` **cannot** be engine-typechecked
or launched without an actual Cocos Creator 3.8 project and its SDK.

## FairyGUI Community: separate compatibility gate

FairyGUI is **not** a runtime dependency yet. After the base scene works:

1. In FairyGUI Community design a minimal avatar, text label, scrolling list,
   and button; manually publish a package to the Cocos project.
2. Integrate the appropriate **3.x** FairyGUI runtime only after checking its
   version/license and compatibility with the exact Cocos 3.8.x editor.
3. Load the UI package, populate avatar/labels with mock data, then reuse the
   canonical image data from the API script for a runtime avatar.
4. Verify open/close, repeat reload, scrolling, missing image fallback,
   cleanup, keyboard/text input, and error behavior. Only then decide whether
   FairyGUI should become an obligatory UI layer.

Generated avatars and card images are runtime data and **do not** require
republishing a FairyGUI UI definition.

## Acceptance status

- [x] Backend API and `image_url` field identified from existing code.
- [x] TypeScript API boundary and headless tests supplied.
- [x] Non-destructive install step and same-origin Web preview helper supplied.
- [ ] Editor-generated Cocos project exists in this branch.
- [ ] Cocos editor imports scripts and the scene runs.
- [ ] Web build loads an actual canonical image from local FastAPI.
- [ ] FairyGUI Community package and dynamic avatar function in Cocos 3.8.
- [ ] Desktop native build runs and releases textures correctly.
- [ ] Owner has manually accepted the UI and interactions.

Reference: [Cocos Creator 3.8 project creation](https://docs.cocos.com/creator/3.8/manual/en/getting-started/helloworld/), [Cocos asset loading](https://docs.cocos.com/creator/3.8/manual/en/asset/dynamic-load-resources.html), [FairyGUI Cocos guide](https://www.fairygui.com/en/docs/sdk/creator/).

## Next: Game Shell room + phone smoke

After the initial `ImagePreviewSmoke` image test, use
[GAME_SHELL.md](GAME_SHELL.md) to create an editor-authored `GameShellSmoke`
scene with a fixed room, an overlay smartphone, Timeline / Messages / Cards
tabs, and an existing canonical image as a demo avatar.

`install_starter.py` now also copies `GameShellController.ts` and
`runtime/GameShellState.ts`. It does **not** replace edited files, create
fake scene metadata, connect FairyGUI automatically, or add new Python APIs.

The navigation state can be checked without Cocos Creator via:

```bash
node --experimental-strip-types --test game-client/tests/*test.mjs
tsc -p game-client/tsconfig.contract.json
```

**Status remains code prepared, not editor-accepted.** The actual UI must still
be created and run using Cocos Creator 3.8.x on the workstation.
