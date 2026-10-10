/**
 * Cocos Creator 3.8 smoke-test component. Attach to a node in a scene CREATED
 * IN THE EDITOR. This file does not manufacture .scene/.prefab/.meta files.
 *
 * First verification target: Web Desktop through the local same-origin dev
 * proxy. Native runtime transport/asset lifecycle still needs its own smoke.
 */
import {
  _decorator,
  assetManager,
  Component,
  ImageAsset,
  Label,
  Sprite,
  SpriteFrame,
  Texture2D,
} from 'cc';
import { ComfyReviewImageApi } from './runtime/ComfyReviewImageApi';

const { ccclass, property } = _decorator;

type OwnedImage = {
  readonly source: ImageAsset;
  readonly texture: Texture2D;
  readonly frame: SpriteFrame;
};

@ccclass('CanonicalImagePreview')
export class CanonicalImagePreview extends Component {
  @property({ type: Sprite })
  public targetSprite: Sprite | null = null;

  @property({ type: Label })
  public statusLabel: Label | null = null;

  @property
  public imageUid = '';

  // Empty = same-origin Web build. For a native build use the actual API host.
  @property
  public apiBaseUrl = '';

  private activeRequest: AbortController | null = null;
  private version = 0;
  private owned: OwnedImage | null = null;
  private disposed = false;

  protected start(): void {
    void this.reload();
  }

  /** Hook this up to a Cocos Button's Click Event in the editor. */
  public reload(): void {
    void this.showImage(this.imageUid);
  }

  /** Reusable from a later card/character preview controller. */
  public setImageUid(imageUid: string): void {
    this.imageUid = imageUid;
    this.reload();
  }

  private async showImage(imageUid: string): Promise<void> {
    const current = ++this.version;
    this.activeRequest?.abort();
    this.activeRequest = new AbortController();
    this.clearImage();

    if (!this.targetSprite) {
      this.setStatus('Sprite-Komponente fehlt');
      return;
    }
    if (!imageUid) {
      this.setStatus('Image-UID im Inspector eintragen');
      return;
    }
    const origin = this.apiBaseUrl.trim() ||
      (typeof window !== 'undefined' ? window.location.origin : '');
    if (!origin) {
      this.setStatus('API-Host fehlt');
      return;
    }

    try {
      this.setStatus('Lade Bildkontext...');
      const api = new ComfyReviewImageApi(origin);
      const ref = await api.loadImageReference(imageUid, this.activeRequest.signal);
      if (this.disposed || current !== this.version) return;
      if (!ref.imageUrl) {
        this.setStatus('Kein verfügbares Bild für diese UID');
        return;
      }

      this.setStatus('Lade Bildtextur...');
      const source = await new Promise<ImageAsset>((resolve, reject) => {
        assetManager.loadRemote<ImageAsset>(ref.imageUrl as string, { ext: '.png' },
          (error, image) => error || !image
            ? reject(error ?? new Error('Leere Bildressource'))
            : resolve(image));
      });
      if (this.disposed || current !== this.version) return;

      // Keep the external asset alive while this preview is visible.
      source.addRef();
      const texture = new Texture2D();
      texture.image = source;
      const frame = new SpriteFrame();
      frame.texture = texture;
      this.owned = { source, texture, frame };
      this.targetSprite.spriteFrame = frame;
      this.setStatus('Bild geladen');
    } catch (error) {
      if (this.disposed || current !== this.version) return;
      if (error instanceof Error && error.name === 'AbortError') return;
      this.setStatus('Laden fehlgeschlagen (Konsole/API prüfen)');
      console.warn('CanonicalImagePreview failed', error);
    }
  }

  private clearImage(): void {
    if (this.targetSprite) this.targetSprite.spriteFrame = null;
    const owned = this.owned;
    this.owned = null;
    if (!owned) return;
    owned.frame.destroy();
    owned.texture.destroy();
    owned.source.decRef();
  }

  private setStatus(value: string): void {
    if (this.statusLabel) this.statusLabel.string = value;
  }

  protected onDestroy(): void {
    this.disposed = true;
    ++this.version;
    this.activeRequest?.abort();
    this.activeRequest = null;
    this.clearImage();
  }
}
