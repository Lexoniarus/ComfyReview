import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClient } from "../../static/js/core/api-client.js";
import { ApiError } from "../../static/js/core/api-error.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ApiClient", () => {
  it("sends JSON requests through the shared API boundary", async () => {
    const fetchMock = vi.fn().mockImplementation(
      async () =>
        new Response(JSON.stringify({ value: 7 }), {
          headers: { "Content-Type": "application/json" },
          status: 200,
        }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = new ApiClient("/api/v2/");

    await expect(client.get("/rankings")).resolves.toEqual({ value: 7 });
    await expect(client.post("reviews", { rating: 8 })).resolves.toEqual({
      value: 7,
    });
    await expect(
      client.put("images/a/curation", { set_key: "pose" }),
    ).resolves.toEqual({
      value: 7,
    });
    await expect(
      client.patch("catalog/a", { archived: true }),
    ).resolves.toEqual({
      value: 7,
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v2/rankings",
      expect.objectContaining({ method: "GET" }),
    );
    const postRequest = fetchMock.mock.calls[1][1];
    expect(postRequest.body).toBe(JSON.stringify({ rating: 8 }));
    expect(postRequest.headers.get("Content-Type")).toBe("application/json");
  });

  it("returns null for an empty successful response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );

    await expect(new ApiClient().post("reviews", {})).resolves.toBeNull();
  });

  it("normalizes API errors with trace context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "invalid_scope",
              message: "Unbekannter Scope.",
              trace_id: "trace-envelope",
            },
          }),
          { status: 400 },
        ),
      ),
    );

    await expect(new ApiClient().get("scopes")).rejects.toEqual(
      expect.objectContaining({
        code: "invalid_scope",
        message: "Unbekannter Scope.",
        status: 400,
        traceId: "trace-envelope",
      }),
    );
  });

  it("uses stable fallbacks for malformed errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "hidden" }), {
          headers: { "X-Request-ID": "trace-header" },
          status: 500,
        }),
      ),
    );

    await expect(new ApiClient().get("broken")).rejects.toEqual(
      expect.objectContaining({
        code: "request_failed",
        message: "Die Anfrage ist fehlgeschlagen.",
        traceId: "trace-header",
      }),
    );
  });

  it("rejects unreadable JSON as a protocol error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("not-json", {
          headers: { "X-Request-ID": "trace-json" },
          status: 200,
        }),
      ),
    );

    await expect(new ApiClient().get("broken")).rejects.toEqual(
      expect.objectContaining({
        code: "invalid_response",
        status: 200,
        traceId: "trace-json",
      }),
    );
  });
});

describe("ApiError", () => {
  it("exposes normalized request details", () => {
    const error = new ApiError({
      code: "missing",
      message: "Nicht gefunden.",
      status: 404,
      traceId: null,
    });

    expect(error).toBeInstanceOf(Error);
    expect(error.name).toBe("ApiError");
    expect(error.code).toBe("missing");
  });
});
