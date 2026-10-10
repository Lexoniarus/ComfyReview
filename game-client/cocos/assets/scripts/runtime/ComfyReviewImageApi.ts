/**
 * Small, dependency-free boundary for the EXISTING ComfyReview API v2.
 * This module is deliberately independent of Cocos Creator and FairyGUI.
 */

export interface CanonicalImageReference {
  readonly imageUid: string;
  readonly imageUrl: string | null;
}

export class ImageApiError extends Error {
  readonly kind: 'input' | 'http' | 'response';
  readonly httpStatus?: number;

  constructor(
    message: string,
    kind: 'input' | 'http' | 'response',
    httpStatus?: number,
  ) {
    super(message);
    this.name = 'ImageApiError';
    this.kind = kind;
    this.httpStatus = httpStatus;
  }
}

export type JsonRequester = (
  url: string,
  signal?: AbortSignal,
) => Promise<unknown>;

export async function requestJsonWithFetch(
  url: string,
  signal?: AbortSignal,
): Promise<unknown> {
  const response = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
    credentials: 'omit',
  });
  if (!response.ok) {
    throw new ImageApiError(
      `ComfyReview returned HTTP ${response.status}`,
      'http',
      response.status,
    );
  }
  return response.json();
}

/**
 * A canonical image's image_url is currently a path such as /files/X.png.
 * Never trust an arbitrary URL from a response as a texture source.
 */
export function parseImageReference(
  body: unknown,
  requestedUid: string,
  serverOrigin: string,
): CanonicalImageReference {
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    throw new ImageApiError('Image response must be an object', 'response');
  }
  const record = body as Record<string, unknown>;
  if (record.image_uid !== requestedUid) {
    throw new ImageApiError('Image response UID does not match request', 'response');
  }
  if (typeof record.image_url !== 'string') {
    throw new ImageApiError('Image response lacks image_url', 'response');
  }
  const relativeUrl = record.image_url;
  if (relativeUrl === '') {
    return { imageUid: requestedUid, imageUrl: null };
  }
  if (!relativeUrl.startsWith('/files/')) {
    throw new ImageApiError('Image URL is not an output file path', 'response');
  }
  const server = new URL(serverOrigin);
  const image = new URL(relativeUrl, server);
  if (
    image.origin !== server.origin ||
    !image.pathname.startsWith('/files/') ||
    image.username !== '' ||
    image.password !== ''
  ) {
    throw new ImageApiError('Image URL points outside ComfyReview files', 'response');
  }
  return { imageUid: requestedUid, imageUrl: image.href };
}

export class ComfyReviewImageApi {
  private readonly base: URL;
  private readonly getJson: JsonRequester;

  constructor(
    baseUrl: string,
    getJson: JsonRequester = requestJsonWithFetch,
  ) {
    this.base = new URL(baseUrl);
    this.getJson = getJson;
    if (!['http:', 'https:'].includes(this.base.protocol)) {
      throw new ImageApiError('ComfyReview must use HTTP or HTTPS', 'input');
    }
    if (this.base.username || this.base.password) {
      throw new ImageApiError('Do not place credentials in the server URL', 'input');
    }
  }

  async loadImageReference(
    imageUid: string,
    signal?: AbortSignal,
  ): Promise<CanonicalImageReference> {
    // The API treats UIDs as opaque. Encode them rather than deriving paths.
    if (!imageUid || imageUid.trim() !== imageUid || imageUid.includes('/') ||
      imageUid === '.' || imageUid === '..' || imageUid.length > 256 ||
      /[?#\\]/.test(imageUid)) {
      throw new ImageApiError('Invalid image UID', 'input');
    }
    const path = `/api/v2/images/${encodeURIComponent(imageUid)}`;
    const url = new URL(path, this.base);
    const body = await this.getJson(url.href, signal);
    return parseImageReference(body, imageUid, this.base.origin);
  }
}
