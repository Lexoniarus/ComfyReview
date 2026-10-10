/**
 * Cocos Creator 3.8 shell controller for a user-authored 2D scene.
 *
 * The room and phone layout are created in the Cocos editor. This script only
 * switches visibility and optionally loads ONE existing canonical image as a
 * demo avatar. FairyGUI is intentionally not required for the first smoke.
 *
 * Bind public methods via Button Click Events in the Inspector. No
 * application-specific backend actions are invented here.
 */
import { _decorator, Component, Label, Node } from 'cc';
import { CanonicalImagePreview } from './CanonicalImagePreview';
import {
  INITIAL_GAME_SHELL_STATE,
  isPhonePanelVisible,
  reduceGameShellState,
  type GameShellAction,
  type GameShellState,
} from './runtime/GameShellState';

const { ccclass, property } = _decorator;

@ccclass('GameShellController')
export class GameShellController extends Component {
  @property({ type: Node })
  public roomRoot: Node | null = null;

  @property({ type: Node })
  public phoneOverlay: Node | null = null;

  @property({ type: Node })
  public timelinePanel: Node | null = null;

  @property({ type: Node })
  public messagesPanel: Node | null = null;

  @property({ type: Node })
  public cardsPanel: Node | null = null;

  @property({ type: Node })
  public avatarPreviewNode: Node | null = null;

  @property({ type: Label })
  public viewStatusLabel: Label | null = null;

  // Optional: use an actual image UID from ComfyReview Studio, not a filepath.
  @property
  public demoAvatarImageUid = '';

  private state: Readonly<GameShellState> = INITIAL_GAME_SHELL_STATE;
  private avatarLoaded = false;

  protected onLoad(): void {
    this.render();
  }

  public openPhone(): void {
    this.dispatch('open-phone');
  }

  public closePhone(): void {
    this.dispatch('close-phone');
  }

  public showTimeline(): void {
    this.dispatch('show-timeline');
  }

  public showMessages(): void {
    this.dispatch('show-messages');
  }

  public showCards(): void {
    this.dispatch('show-cards');
  }

  private dispatch(action: GameShellAction): void {
    const oldState = this.state;
    const newState = reduceGameShellState(oldState, action);
    if (newState === oldState) return;
    this.state = newState;
    this.render();

    const messagesVisible = isPhonePanelVisible(newState, 'messages');
    if (messagesVisible && !this.avatarLoaded) {
      this.avatarLoaded = true;
      this.avatarPreviewNode
        ?.getComponent(CanonicalImagePreview)
        ?.setImageUid(this.demoAvatarImageUid.trim());
    } else if (!messagesVisible && this.avatarLoaded) {
      // Release the preview texture when the user leaves the chat panel.
      this.avatarLoaded = false;
      this.avatarPreviewNode
        ?.getComponent(CanonicalImagePreview)
        ?.setImageUid('');
    }
  }

  private render(): void {
    const phoneVisible = this.state.screen === 'phone';
    if (this.roomRoot) this.roomRoot.active = true;
    if (this.phoneOverlay) this.phoneOverlay.active = phoneVisible;
    if (this.timelinePanel) {
      this.timelinePanel.active = isPhonePanelVisible(this.state, 'timeline');
    }
    if (this.messagesPanel) {
      this.messagesPanel.active = isPhonePanelVisible(this.state, 'messages');
    }
    if (this.cardsPanel) {
      this.cardsPanel.active = isPhonePanelVisible(this.state, 'cards');
    }
    if (this.viewStatusLabel) {
      this.viewStatusLabel.string = phoneVisible
        ? `Telefon · ${this.state.phoneTab}`
        : 'Raum';
    }
  }

  protected onDestroy(): void {
    this.avatarLoaded = false;
  }
}
