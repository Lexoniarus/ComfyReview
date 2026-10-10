/**
 * CC-GAME-02 scene controller. The checked-in Cocos scene supplies Canvas,
 * RoomRoot, PhoneOverlay and the original OpenPhoneButton Click Event.
 * Temporary room/phone visuals and the remaining buttons are created by code.
 */
import { _decorator, Component, Label, Node } from 'cc';
import { CanonicalImagePreview } from './CanonicalImagePreview';
import { GameShellViewBuilder, type GameShellView } from './GameShellView';
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

  // Optional existing ComfyReview demo image, not required for mock navigation.
  @property
  public demoAvatarImageUid = '';

  private state: Readonly<GameShellState> = INITIAL_GAME_SHELL_STATE;
  private view: GameShellView | null = null;
  private avatarLoaded = false;

  protected onLoad(): void {
    if (!this.roomRoot || !this.phoneOverlay) {
      console.error('GameShell.scene: RoomRoot / PhoneOverlay missing in Inspector');
      return;
    }
    this.view = new GameShellViewBuilder(this.roomRoot, this.phoneOverlay, {
      closePhone: () => this.closePhone(),
      showTimeline: () => this.showTimeline(),
      showMessages: () => this.showMessages(),
      showCards: () => this.showCards(),
    }).build();
    this.timelinePanel = this.view.timelinePanel;
    this.messagesPanel = this.view.messagesPanel;
    this.cardsPanel = this.view.cardsPanel;
    this.render();
  }

  // openPhone is still connected by the existing editor-authored Click Event.
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
    const newState = reduceGameShellState(this.state, action);
    if (newState === this.state) return;
    this.state = newState;
    this.render();
    this.syncOptionalAvatar();
  }

  private syncOptionalAvatar(): void {
    const preview = this.avatarPreviewNode?.getComponent(CanonicalImagePreview);
    const imageUid = this.demoAvatarImageUid.trim();
    const shouldShow = isPhonePanelVisible(this.state, 'messages') &&
      Boolean(imageUid) && Boolean(preview);
    if (shouldShow && !this.avatarLoaded) {
      this.avatarLoaded = true;
      preview?.setImageUid(imageUid);
    } else if (!shouldShow && this.avatarLoaded) {
      this.avatarLoaded = false;
      preview?.setImageUid('');
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
    if (phoneVisible) this.view?.selectTab(this.state.phoneTab);
    if (this.viewStatusLabel) {
      this.viewStatusLabel.string = phoneVisible
        ? `Telefon · ${this.state.phoneTab}`
        : 'Raum';
    }
  }

  protected onDestroy(): void {
    // Generated UI nodes and their Button listeners are owned by the scene.
    // CanonicalImagePreview owns/disposes its optional image resources.
    this.view = null;
    this.avatarLoaded = false;
  }
}
