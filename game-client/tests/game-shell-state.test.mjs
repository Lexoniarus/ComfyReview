import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import {
  INITIAL_GAME_SHELL_STATE,
  isPhonePanelVisible,
  reduceGameShellState,
} from '../cocos/assets/scripts/runtime/GameShellState.ts';

const dispatch = (...actions) => actions.reduce(
  (state, action) => reduceGameShellState(state, action),
  INITIAL_GAME_SHELL_STATE,
);

test('initial screen is the fixed room with an unopened phone', () => {
  assert.deepEqual(INITIAL_GAME_SHELL_STATE, {
    screen: 'room', phoneTab: 'timeline',
  });
  assert.equal(isPhonePanelVisible(INITIAL_GAME_SHELL_STATE, 'timeline'), false);
});

test('opening the phone shows timeline but not messages or cards', () => {
  const state = dispatch('open-phone');
  assert.equal(state.screen, 'phone');
  assert.equal(isPhonePanelVisible(state, 'timeline'), true);
  assert.equal(isPhonePanelVisible(state, 'messages'), false);
  assert.equal(isPhonePanelVisible(state, 'cards'), false);
});

test('a tab action can open phone and selects exactly that tab', () => {
  const state = dispatch('show-messages');
  assert.deepEqual(state, { screen: 'phone', phoneTab: 'messages' });
  assert.equal(isPhonePanelVisible(state, 'messages'), true);
});

test('closing the phone returns to room and remembers the tab', () => {
  const state = dispatch('open-phone', 'show-cards', 'close-phone');
  assert.deepEqual(state, { screen: 'room', phoneTab: 'cards' });
  assert.equal(isPhonePanelVisible(state, 'cards'), false);
  assert.deepEqual(reduceGameShellState(state, 'open-phone'), {
    screen: 'phone', phoneTab: 'cards',
  });
});

test('repeated actions are referentially idempotent', () => {
  const open = dispatch('open-phone');
  assert.equal(reduceGameShellState(open, 'open-phone'), open);
  assert.equal(reduceGameShellState(open, 'show-timeline'), open);
  assert.equal(
    reduceGameShellState(INITIAL_GAME_SHELL_STATE, 'close-phone'),
    INITIAL_GAME_SHELL_STATE,
  );
});

test('independent sessions do not mutate their initial state', () => {
  const state = dispatch('show-messages', 'show-cards');
  assert.deepEqual(state, { screen: 'phone', phoneTab: 'cards' });
  assert.deepEqual(INITIAL_GAME_SHELL_STATE, {
    screen: 'room', phoneTab: 'timeline',
  });
});

test('each tab is exclusively visible during repeated navigation', () => {
  let state = INITIAL_GAME_SHELL_STATE;
  for (let index = 0; index < 60; index += 1) {
    const tab = ['timeline', 'messages', 'cards'][index % 3];
    state = reduceGameShellState(state, `show-${tab}`);
    assert.equal(state.screen, 'phone');
    for (const candidate of ['timeline', 'messages', 'cards']) {
      assert.equal(isPhonePanelVisible(state, candidate), candidate === tab);
    }
  }
});

test('repeated open/close cycles retain the tab and never add backend state', () => {
  let state = INITIAL_GAME_SHELL_STATE;
  for (let index = 0; index < 100; index += 1) {
    state = reduceGameShellState(state, 'open-phone');
    state = reduceGameShellState(state, 'show-messages');
    state = reduceGameShellState(state, 'close-phone');
    assert.deepEqual(state, { screen: 'room', phoneTab: 'messages' });
    assert.deepEqual(Object.keys(state).sort(), ['phoneTab', 'screen']);
  }
  assert.deepEqual(INITIAL_GAME_SHELL_STATE, {
    screen: 'room', phoneTab: 'timeline',
  });
});

test('editor-backed runtime and optional installer source are identical', () => {
  for (const path of [
    'GameShellController.ts',
    'GameShellView.ts',
    'runtime/GameShellState.ts',
  ]) {
    const cocos = new URL(`../cocos/assets/scripts/${path}`, import.meta.url);
    const starter = new URL(`../starter/assets/scripts/${path}`, import.meta.url);
    assert.equal(readFileSync(fileURLToPath(cocos), 'utf8'),
      readFileSync(fileURLToPath(starter), 'utf8'));
  }
});
