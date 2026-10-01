import { beforeEach, describe, expect, it, vi } from "vitest";

import { ScopeStateController } from "../../static/js/scopes/scope-state-controller.js";
import {
  normalizeScopes,
  readScopeUrlState,
  writeScopeUrlState,
} from "../../static/js/scopes/url-state.js";

describe("scope URL state", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/top_pictures");
  });

  it("round-trips repeated scopes and canonical filters", () => {
    const state = readScopeUrlState(
      "?scope=b&scope=a&scope=a&classification=classified&model= anime " +
        "&checkpoint=base&set_key=favorite&mode=worst&offset=48",
    );

    expect(state).toEqual({
      scopes: ["a", "b"],
      classification: "classified",
      model: "anime",
      checkpoint: "base",
      setKey: "favorite",
      mode: "worst",
      offset: 48,
    });
    expect(writeScopeUrlState(state)).toBe(
      "?scope=a&scope=b&classification=classified&model=anime&" +
        "checkpoint=base&set_key=favorite&mode=worst&offset=48",
    );
  });

  it("normalizes invalid and empty URL values", () => {
    expect(
      readScopeUrlState("?classification=nope&mode=new&offset=-2"),
    ).toEqual({
      scopes: [],
      classification: "all",
      model: "",
      checkpoint: "",
      setKey: "",
      mode: "top",
      offset: 0,
    });
    expect(writeScopeUrlState(readScopeUrlState(""))).toBe("");
    expect(normalizeScopes([" a ", "", "a", "b"])).toEqual(["a", "b"]);
  });

  it("owns push, replace, popstate, subscriptions, and disposal", () => {
    const push = vi.spyOn(window.history, "pushState");
    const replace = vi.spyOn(window.history, "replaceState");
    const listener = vi.fn();
    const controller = new ScopeStateController(window);
    const unsubscribe = controller.subscribe(listener);

    controller.start();
    controller.start();
    controller.update({ scopes: ["b", "a"], offset: 96 });
    controller.update({ mode: "worst", offset: 48 }, { replace: true });
    window.history.replaceState(
      null,
      "",
      "/top_pictures?classification=unclassified",
    );
    window.dispatchEvent(new PopStateEvent("popstate"));

    expect(push).toHaveBeenCalledWith(
      null,
      "",
      "/top_pictures?scope=a&scope=b&offset=96",
    );
    expect(replace).toHaveBeenCalledWith(
      null,
      "",
      "/top_pictures?scope=a&scope=b&mode=worst&offset=48",
    );
    expect(controller.state.classification).toBe("unclassified");
    expect(listener).toHaveBeenCalledTimes(4);

    unsubscribe();
    controller.dispose();
    controller.dispose();
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(listener).toHaveBeenCalledTimes(4);
  });
});
