/**
 * Temporary Cocos-only presentation for CC-GAME-02.
 * Uses the editor-authored RoomRoot, PhoneOverlay and OpenPhoneButton.
 * No game data, generated art, network requests or save state lives here.
 */
import {
  BlockInputEvents,
  Button,
  Color,
  Graphics,
  Label,
  Layers,
  Node,
  UITransform,
} from 'cc';
import type { PhoneTab } from './runtime/GameShellState';

export interface GameShellViewActions {
  readonly closePhone: () => void;
  readonly showTimeline: () => void;
  readonly showMessages: () => void;
  readonly showCards: () => void;
}

export interface GameShellView {
  readonly timelinePanel: Node;
  readonly messagesPanel: Node;
  readonly cardsPanel: Node;
  selectTab(tab: PhoneTab): void;
}

const COLOR = {
  wall: new Color(31, 43, 61),
  wallTrim: new Color(41, 57, 77),
  floor: new Color(60, 57, 73),
  window: new Color(68, 101, 128),
  windowLight: new Color(114, 153, 168),
  furniture: new Color(49, 67, 86),
  furnitureTop: new Color(92, 104, 123),
  muted: new Color(162, 181, 200),
  white: new Color(238, 244, 248),
  accent: new Color(98, 205, 191),
  accentDark: new Color(33, 92, 99),
  overlay: new Color(8, 13, 25, 205),
  phone: new Color(17, 27, 43),
  content: new Color(28, 41, 60),
  surface: new Color(39, 56, 77),
  selected: new Color(48, 112, 116),
  neutralTab: new Color(43, 59, 78),
} as const;

/** Create UI nodes on the 2D UI layer; the scene and Canvas remain editor-owned. */
function uiNode(
  parent: Node,
  name: string,
  x: number,
  y: number,
  width: number,
  height: number,
): Node {
  const node = new Node(name);
  node.layer = Layers.Enum.UI_2D;
  parent.addChild(node);
  node.setPosition(x, y, 0);
  node.addComponent(UITransform).setContentSize(width, height);
  return node;
}

function paint(graphics: Graphics, width: number, height: number, color: Color): void {
  graphics.clear();
  graphics.fillColor = color;
  graphics.rect(-width / 2, -height / 2, width, height);
  graphics.fill();
}

function rectangle(
  parent: Node,
  name: string,
  x: number,
  y: number,
  width: number,
  height: number,
  color: Color,
): Node {
  const node = uiNode(parent, name, x, y, width, height);
  paint(node.addComponent(Graphics), width, height, color);
  return node;
}

function label(
  parent: Node,
  name: string,
  value: string,
  x: number,
  y: number,
  width: number,
  height: number,
  fontSize: number,
  color: Color = COLOR.white,
  leftAligned = false,
): Label {
  const node = uiNode(parent, name, x, y, width, height);
  const component = node.addComponent(Label);
  component.useSystemFont = true;
  component.fontFamily = 'Arial';
  component.string = value;
  component.fontSize = fontSize;
  component.lineHeight = fontSize + 7;
  component.color = color;
  component.horizontalAlign = leftAligned
    ? Label.HorizontalAlign.LEFT
    : Label.HorizontalAlign.CENTER;
  component.verticalAlign = Label.VerticalAlign.CENTER;
  component.overflow = Label.Overflow.SHRINK;
  component.enableWrapText = true;
  return component;
}

interface ButtonView {
  readonly node: Node;
  readonly graphics: Graphics;
  readonly text: Label;
  readonly width: number;
  readonly height: number;
}

function button(
  parent: Node,
  name: string,
  value: string,
  x: number,
  y: number,
  width: number,
  height: number,
  color: Color,
  onClick: () => void,
): ButtonView {
  const node = uiNode(parent, name, x, y, width, height);
  const graphics = node.addComponent(Graphics);
  paint(graphics, width, height, color);
  const click = node.addComponent(Button);
  click.transition = Button.Transition.SCALE;
  click.zoomScale = 0.96;
  node.on(Button.EventType.CLICK, onClick);
  const text = label(node, `${name}Label`, value, 0, 0, width - 12, height - 4, 18);
  return { node, graphics, text, width, height };
}

/** Code-generated mock UI, not a serialized Cocos scene or prefab. */
export class GameShellViewBuilder {
  constructor(
    private readonly roomRoot: Node,
    private readonly phoneOverlay: Node,
    private readonly actions: GameShellViewActions,
  ) {}

  public build(): GameShellView {
    this.buildRoom();
    return this.buildPhone();
  }

  private buildRoom(): void {
    const screen = this.roomRoot.parent?.getComponent(UITransform)?.contentSize;
    const width = screen?.width ?? 1280;
    const height = screen?.height ?? 720;
    const art = uiNode(this.roomRoot, 'GeneratedRoomVisuals', 0, 0, width, height);
    art.setSiblingIndex(0); // Keep the actual editor-authored OpenPhoneButton on top.

    rectangle(art, 'Wall', 0, 0, width, height, COLOR.wall);
    rectangle(art, 'WallTrim', 0, -194, width, 16, COLOR.wallTrim);
    rectangle(art, 'Floor', 0, -292, width, 186, COLOR.floor);
    rectangle(art, 'Rug', 0, -258, 630, 97, COLOR.furniture);
    rectangle(art, 'WindowFrame', -351, 89, 292, 245, COLOR.furnitureTop);
    rectangle(art, 'WindowGlass', -351, 89, 274, 224, COLOR.window);
    rectangle(art, 'WindowSky', -351, 127, 266, 136, COLOR.windowLight);
    rectangle(art, 'WindowDivider', -351, 89, 9, 227, COLOR.furnitureTop);
    rectangle(art, 'WindowSill', -351, -32, 316, 16, COLOR.furnitureTop);

    rectangle(art, 'Cabinet', 374, -39, 204, 296, COLOR.furniture);
    for (const y of [-124, -37, 50]) {
      rectangle(art, `CabinetShelf${y}`, 374, y, 210, 11, COLOR.furnitureTop);
    }
    rectangle(art, 'DeskTop', -30, -171, 405, 41, COLOR.furnitureTop);
    rectangle(art, 'DeskLegLeft', -198, -235, 21, 100, COLOR.furniture);
    rectangle(art, 'DeskLegRight', 140, -235, 21, 100, COLOR.furniture);
    rectangle(art, 'Laptop', -31, -120, 134, 81, COLOR.furniture);
    rectangle(art, 'LaptopScreen', -31, -122, 122, 67, COLOR.window);

    label(art, 'RoomHeading', 'CHARACTER CHRONICLES  ·  DEMO',
      -334, 301, 575, 34, 24, COLOR.white, true);
    label(art, 'RoomHint', 'Raum-Hub / vorläufige Platzhalterdarstellung',
      -334, 269, 575, 32, 17, COLOR.muted, true);
    label(art, 'RoomHintPhone', 'Öffne dein Smartphone, um die Demo-Apps anzusehen.',
      0, -320, 760, 26, 16, COLOR.white);

    // This is the actual Cocos-editor Button with its existing Click Event.
    const opener = this.roomRoot.getChildByName('OpenPhoneButton');
    const openerButton = opener?.getComponent(Button);
    if (!opener || !openerButton) {
      throw new Error('GameShell.scene: OpenPhoneButton (Button) fehlt');
    }
    opener.setPosition(0, -257, 0);
    opener.getComponent(UITransform)?.setContentSize(294, 58);
    openerButton.transition = Button.Transition.SCALE;
    openerButton.zoomScale = 0.96;
    const background = rectangle(opener, 'GeneratedOpenButtonSurface',
      0, 0, 294, 58, COLOR.accent);
    background.setSiblingIndex(0);
    const openerText = opener.getChildByName('Label')?.getComponent(Label);
    if (openerText) {
      openerText.string = 'Smartphone öffnen';
      openerText.fontSize = 21;
      openerText.lineHeight = 28;
      openerText.color = COLOR.phone;
    }
  }

  private buildPhone(): GameShellView {
    if (!this.phoneOverlay.getComponent(BlockInputEvents)) {
      this.phoneOverlay.addComponent(BlockInputEvents);
    }
    const screen = this.roomRoot.parent?.getComponent(UITransform)?.contentSize;
    const width = screen?.width ?? 1280;
    const height = screen?.height ?? 720;
    this.phoneOverlay.getComponent(UITransform)?.setContentSize(width, height);
    const art = uiNode(this.phoneOverlay, 'GeneratedPhoneVisuals', 0, 0, width, height);
    rectangle(art, 'DimRoom', 0, 0, width, height, COLOR.overlay);
    const frame = rectangle(art, 'PhoneFrame', 0, 0, 598, 660, COLOR.phone);
    rectangle(frame, 'PhoneHeader', 0, 281, 568, 73, COLOR.furniture);
    label(frame, 'PhoneTitle', 'SMARTPHONE', -126, 288, 300, 38, 25);
    label(frame, 'DemoBadge', 'DEMO', 111, 287, 80, 34, 15, COLOR.accent);
    button(frame, 'ClosePhoneButton', 'X', 251, 284, 52, 48,
      COLOR.accentDark, this.actions.closePhone);

    const tabs: Record<PhoneTab, ButtonView> = {
      timeline: button(frame, 'TimelineTab', 'Timeline', -178, 207, 164, 54,
        COLOR.neutralTab, this.actions.showTimeline),
      messages: button(frame, 'MessagesTab', 'Nachrichten', 0, 207, 164, 54,
        COLOR.neutralTab, this.actions.showMessages),
      cards: button(frame, 'CardsTab', 'Karten', 178, 207, 164, 54,
        COLOR.neutralTab, this.actions.showCards),
    };

    const timelinePanel = rectangle(frame, 'TimelinePanel', 0, -30,
      546, 397, COLOR.content);
    this.buildTimeline(timelinePanel);
    const messagesPanel = rectangle(frame, 'MessagesPanel', 0, -30,
      546, 397, COLOR.content);
    this.buildMessages(messagesPanel);
    const cardsPanel = rectangle(frame, 'CardsPanel', 0, -30,
      546, 397, COLOR.content);
    this.buildCards(cardsPanel);
    label(frame, 'PhoneFooter', 'LOKALE UI-DEMO · keine Spielstände oder Serveraktionen',
      0, -295, 540, 28, 14, COLOR.muted);

    return {
      timelinePanel,
      messagesPanel,
      cardsPanel,
      selectTab: (tab: PhoneTab): void => {
        for (const key of ['timeline', 'messages', 'cards'] as const) {
          const item = tabs[key];
          const selected = key === tab;
          paint(item.graphics, item.width, item.height,
            selected ? COLOR.selected : COLOR.neutralTab);
          item.text.color = selected ? COLOR.white : COLOR.muted;
        }
      },
    };
  }

  private buildTimeline(parent: Node): void {
    label(parent, 'TimelineTitle', 'TIMELINE  ·  DEMO',
      -11, 162, 500, 38, 23, COLOR.accent, true);
    rectangle(parent, 'TimelinePostOne', 0, 61, 504, 128, COLOR.surface);
    label(parent, 'TimelinePostOneText',
      'DEMO-PROFIL A  ·  Beispielpost\nEin erster Tag in der Stadt. Was gibt es zu entdecken?',
      0, 61, 474, 105, 18, COLOR.white, true);
    rectangle(parent, 'TimelinePostTwo', 0, -88, 504, 128, COLOR.surface);
    label(parent, 'TimelinePostTwoText',
      'DEMO-PROFIL B  ·  Beispielpost\nHeute ein paar Kartenideen gesammelt. Noch ist alles Mock.',
      0, -88, 474, 105, 18, COLOR.white, true);
    label(parent, 'TimelineFootnote', 'Keine echten Posts und kein Social-Backend.',
      0, -173, 485, 28, 15, COLOR.muted);
  }

  private buildMessages(parent: Node): void {
    label(parent, 'MessagesTitle', 'NACHRICHTEN  ·  DEMO',
      -11, 162, 500, 38, 23, COLOR.accent, true);
    rectangle(parent, 'IncomingBubble', -47, 61, 406, 116, COLOR.surface);
    label(parent, 'IncomingText',
      'DEMO-KONTAKT\nHallo! Dies ist eine Beispielnachricht.',
      -47, 61, 372, 94, 19, COLOR.white, true);
    rectangle(parent, 'OutgoingBubble', 47, -81, 406, 116, COLOR.accentDark);
    label(parent, 'OutgoingText',
      'DU (DEMO)\nDas Smartphone lässt sich bereits bedienen.',
      47, -81, 372, 94, 19, COLOR.white, true);
    label(parent, 'MessagesFootnote', 'Kein Chatversand, keine LLM-Antworten, keine Speicherung.',
      0, -173, 510, 28, 15, COLOR.muted);
  }

  private buildCards(parent: Node): void {
    label(parent, 'CardsTitle', 'KARTEN  ·  DEMO',
      -11, 162, 500, 38, 23, COLOR.accent, true);
    const positions = [-171, 0, 171];
    for (let index = 0; index < positions.length; index += 1) {
      const card = rectangle(parent, `MockCard${index + 1}`,
        positions[index], -13, 149, 227, COLOR.surface);
      rectangle(card, 'MockArt', 0, 32, 121, 124, COLOR.window);
      label(card, 'MockArtLabel', 'PLATZHALTER', 0, 32, 118, 30, 14, COLOR.white);
      label(card, 'MockCardLabel', `DEMO-KARTE ${index + 1}`,
        0, -81, 138, 44, 17, COLOR.white);
    }
    label(parent, 'CardsFootnote', 'Keine Kartensammlung und keine Card-Battler-API.',
      0, -174, 515, 28, 15, COLOR.muted);
  }
}
