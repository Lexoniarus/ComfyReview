/**
 * Presentation-only navigation for the Character Chronicles game-client shell.
 *
 * No save-game, social, card, or Python business rules belong here. The first
 * implementation deliberately works with mock UI and no new API endpoints.
 */
export type GameShellScreen = 'room' | 'phone';
export type PhoneTab = 'timeline' | 'messages' | 'cards';

export interface GameShellState {
  readonly screen: GameShellScreen;
  readonly phoneTab: PhoneTab;
}

export type GameShellAction =
  | 'open-phone'
  | 'close-phone'
  | 'show-timeline'
  | 'show-messages'
  | 'show-cards';

export const INITIAL_GAME_SHELL_STATE: Readonly<GameShellState> = Object.freeze({
  screen: 'room',
  phoneTab: 'timeline',
});

/** Keep the last selected tab when closing the phone. */
export function reduceGameShellState(
  state: Readonly<GameShellState>,
  action: GameShellAction,
): Readonly<GameShellState> {
  switch (action) {
    case 'open-phone':
      return state.screen === 'phone'
        ? state
        : { ...state, screen: 'phone' };
    case 'close-phone':
      return state.screen === 'room'
        ? state
        : { ...state, screen: 'room' };
    case 'show-timeline':
      return showTab(state, 'timeline');
    case 'show-messages':
      return showTab(state, 'messages');
    case 'show-cards':
      return showTab(state, 'cards');
  }
}

function showTab(
  state: Readonly<GameShellState>,
  phoneTab: PhoneTab,
): Readonly<GameShellState> {
  return state.screen === 'phone' && state.phoneTab === phoneTab
    ? state
    : { screen: 'phone', phoneTab };
}

export function isPhonePanelVisible(
  state: Readonly<GameShellState>,
  tab: PhoneTab,
): boolean {
  return state.screen === 'phone' && state.phoneTab === tab;
}
