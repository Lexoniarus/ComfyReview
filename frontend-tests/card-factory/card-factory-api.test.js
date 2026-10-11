import { describe, expect, it, vi } from "vitest";

import { CardFactoryApi } from "../../static/js/card-factory/card-factory-api.js";

describe("CardFactoryApi", () => {
  it("maps every Card Factory operation onto the shared API client", async () => {
    const client = {
      get: vi.fn(() => Promise.resolve({})),
      post: vi.fn(() => Promise.resolve({})),
    };
    const api = new CardFactoryApi(client);
    const signal = new AbortController().signal;

    await api.sources({ offset: 24, limit: 12, signal });
    await api.create("image 1", { signal });
    await api.session("session 1", { signal });
    await api.generate("session 1", 2, { signal });
    await api.develop("session 1", 3, { signal });
    await api.accept("session 1", "candidate 1", 4, { signal });

    expect(client.get).toHaveBeenNthCalledWith(
      1,
      "card-factory/sources?offset=24&limit=12",
      { signal },
    );
    expect(client.get).toHaveBeenNthCalledWith(
      2,
      "card-factory/sessions/session%201",
      { signal },
    );
    expect(client.post).toHaveBeenNthCalledWith(
      1,
      "card-factory/sessions",
      { image_uid: "image 1" },
      { signal },
    );
    expect(client.post).toHaveBeenNthCalledWith(
      2,
      "card-factory/sessions/session%201/candidates",
      { expected_revision: 2 },
      { signal },
    );
    expect(client.post).toHaveBeenNthCalledWith(
      3,
      "card-factory/sessions/session%201/develop",
      { expected_revision: 3 },
      { signal },
    );
    expect(client.post).toHaveBeenNthCalledWith(
      4,
      "card-factory/sessions/session%201/candidates/candidate%201/accept",
      { expected_revision: 4 },
      { signal },
    );
  });
});
