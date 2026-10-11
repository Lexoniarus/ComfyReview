import { beforeEach, describe, expect, it, vi } from "vitest";

import { CardCandidateGroupOverview } from "../../static/js/card-factory/group-overview.js";

describe("CardCandidateGroupOverview", () => {
  beforeEach(() => {
    document.body.innerHTML = `<main data-card-candidate-groups>
      <span data-group-overview-status></span>
      <div data-group-overview-content></div>
    </main>`;
  });

  it("groups server states and polls only while work is active", async () => {
    const fixture = setup([
      group("queued", "group-running"),
      group("ready", "group-ready"),
      group("partial_failure", "group-partial"),
      group("completed", "group-completed"),
      group("rejected", "group-rejected"),
    ]);

    await fixture.overview.start();

    expect(document.querySelectorAll(".candidate-group-tile")).toHaveLength(5);
    expect(
      document.querySelector('[data-group-lane="ready"] strong').textContent,
    ).toBe("Vier Karten bereit");
    expect(fixture.requests.schedule).toHaveBeenCalledOnce();
    fixture.requests.schedule.mock.calls[0][0]();
    await settle();
    expect(fixture.api.groups).toHaveBeenCalledTimes(2);
    fixture.overview.dispose();
    expect(fixture.requests.dispose).toHaveBeenCalledOnce();
  });

  it("renders empty and failed loads without unsafe markup", async () => {
    const empty = setup([]);
    await empty.overview.start();
    expect(document.querySelector(".card-empty-state").textContent).toContain(
      "Noch keine",
    );

    const failed = setup([], new Error("offline"));
    await failed.overview.start();
    expect(document.querySelector(".card-error-state").textContent).toBe(
      "offline",
    );
  });
});

function setup(groups, error = null) {
  const api = {
    groups: vi.fn(() =>
      error ? Promise.reject(error) : Promise.resolve({ items: groups }),
    ),
  };
  const requests = {
    run: vi.fn((operation) => operation(new AbortController().signal)),
    schedule: vi.fn(() => 7),
    cancel: vi.fn(),
    cancelRequests: vi.fn(),
    dispose: vi.fn(),
  };
  return {
    api,
    requests,
    overview: new CardCandidateGroupOverview({
      root: document.querySelector("main"),
      api,
      requests,
      pollInterval: 1,
    }),
  };
}

function group(status, groupId) {
  return {
    group_id: groupId,
    kind: "initial",
    status,
    source: { image_url: "/source.png" },
    candidates: Array.from({ length: 4 }, (_, index) => ({
      status: index < 2 ? "completed" : "submitted",
    })),
  };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
}
