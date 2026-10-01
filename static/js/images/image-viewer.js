/** Own the full-size image dialog and its lifecycle. */
export class ImageViewer {
  /** @param {HTMLDialogElement} dialog */
  constructor(dialog) {
    this.dialog = dialog;
    const image = dialog.querySelector("img");
    if (!(image instanceof HTMLImageElement)) {
      throw new Error("Image viewer requires an img element");
    }
    this.image = image;
    this.events = new AbortController();
    this.dialog.addEventListener(
      "click",
      (event) => {
        const target = event.target;
        if (
          target === this.dialog ||
          (target instanceof Element && target.closest("[data-viewer-close]"))
        ) {
          this.close();
        }
      },
      { signal: this.events.signal },
    );
  }

  /** @param {string} url */
  open(url) {
    if (!url) return;
    this.image.src = url;
    this.dialog.showModal();
  }

  /** Close the viewer and release its image resource. */
  close() {
    if (this.dialog.open) {
      this.dialog.close();
    }
    this.image.removeAttribute("src");
  }

  /** Release every DOM listener owned by this component. */
  dispose() {
    this.close();
    this.events.abort();
  }
}
