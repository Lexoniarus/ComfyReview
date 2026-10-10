import test from 'node:test';
import assert from 'node:assert/strict';
import {
  INITIAL_GAME_SHELL_STATE,
  isPhonePanelVisible,
  reduceGameShellState,
} from '../starter/assets/scripts/runtime/GameShellState.ts';

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
