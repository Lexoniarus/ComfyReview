import { beforeEach, describe, expect, it } from "vitest";

import { ResponsiveRails } from "../../static/js/layout/responsive-rails.js";

describe("ResponsiveRails", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("keeps drawers mutually exclusive and reflects expanded state", () => {
    const root = document.createElement("main");
    root.insertAdjacentHTML(
      "beforeend",
      "<button data-rail-action='scope'></button>" +
        "<button data-rail-action='inspector'></button>",
    );
    document.body.append(root);
    const rails = new ResponsiveRails(root);

    root.querySelector("[data-rail-action='scope']")?.click();
    expect(root.classList.contains("is-scope-open")).toBe(true);
    root.querySelector("[data-rail-action='inspector']")?.click();
    expect(root.classList.contains("is-scope-open")).toBe(false);
    expect(root.classList.contains("is-inspector-open")).toBe(true);
    expect(
      root
        .querySelector("[data-rail-action='scope']")
        ?.getAttribute("aria-expanded"),
    ).toBe("false");
    root.querySelector("[data-rail-action='inspector']")?.click();
    expect(root.classList.contains("is-inspector-open")).toBe(false);

    root.click();
    const textTarget = document.createTextNode("text");
    root.append(textTarget);
    textTarget.dispatchEvent(new Event("click", { bubbles: true }));
    const unknown = document.createElement("button");
    unknown.dataset.railAction = "unknown";
    root.append(unknown);
    unknown.click();
    rails.dispose();
    root.querySelector("[data-rail-action='scope']")?.click();
    expect(root.classList.contains("is-scope-open")).toBe(false);
  });

  it("can be controlled by an orchestrator", () => {
    const root = document.createElement("main");
    const rails = new ResponsiveRails(root);

    rails.toggle("scope");
    rails.open("scope");

    expect(root.classList.contains("is-scope-open")).toBe(true);
  });
});
