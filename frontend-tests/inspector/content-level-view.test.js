import { beforeEach, describe, expect, it, vi } from "vitest";

import { ContentLevelView } from "../../static/js/inspector/content-level-view.js";

describe("ContentLevelView", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("renders automatic and manual levels and delegates available actions", () => {
    const onAssign = vi.fn();
    const onDelete = vi.fn();
    const view = new ContentLevelView({ onAssign, onDelete });
    document.body.append(view.element);

    view.render({
      image_uid: "image/1",
      content_classification: {
        inferred_level: "lewd",
        effective_level: "nude",
        override_level: "nude",
      },
    });
    expect(view.element.textContent).toContain("Automatisch: Lewd");
    const select = view.element.querySelector("[data-content-level]");
    expect(select).toBeInstanceOf(HTMLSelectElement);
    expect(select.value).toBe("nude");

    select.value = "";
    view.element.querySelector("[data-content-action='assign']")?.click();
    expect(onAssign).toHaveBeenCalledWith("image/1", null);
    select.value = "explicit";
    view.element.querySelector("[data-content-action='assign']")?.click();
    expect(onAssign).toHaveBeenLastCalledWith("image/1", "explicit");
    view.element.querySelector("[data-content-action='delete']")?.click();
    expect(onDelete).toHaveBeenCalledWith("image/1");

    view.setBusy(true);
    expect(select.disabled).toBe(true);
    view.setBusy(false);
    expect(select.disabled).toBe(false);
    view.showError("Speichern fehlgeschlagen");
    expect(view.element.textContent).toContain("Speichern fehlgeschlagen");

    view.render({ image_uid: "image-2" });
    expect(view.element.textContent).toContain("Automatisch: Standard");
    view.dispose();
    view.element.querySelector("[data-content-action='delete']")?.click();
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("shows classification read-only when no mutation actions exist", () => {
    const view = new ContentLevelView();
    document.body.append(view.element);
    view.showError("ignored before render");
    view.render({ image_uid: "", content_classification: {} });

    expect(view.element.querySelector("select")).toBeNull();
    expect(view.element.querySelector("button")).toBeNull();
    view.element.click();
    const text = document.createTextNode("text");
    view.element.append(text);
    text.dispatchEvent(new Event("click", { bubbles: true }));
    view.dispose();
  });

  it("ignores unrelated elements while keeping assign-only controls", () => {
    const onAssign = vi.fn();
    const view = new ContentLevelView({ onAssign });
    document.body.append(view.element);
    view.render({ image_uid: "image-3" });

    expect(
      view.element.querySelector("[data-content-action='delete']"),
    ).toBeNull();
    view.element.querySelector("h3")?.click();
    expect(onAssign).not.toHaveBeenCalled();
  });
});
