import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ComfyReviewImageApi,
  ImageApiError,
  parseImageReference,
  requestJsonWithFetch,
} from '../starter/assets/scripts/runtime/ComfyReviewImageApi.ts';

const BASE = 'http://127.0.0.1:8000/';
const valid = (uid = 'img-123', url = '/files/stage/example.png') => ({
  image_uid: uid, image_url: url,
});

test('canonical image context returns same-origin output URL', async () => {
  let requestUrl = '';
  const api = new ComfyReviewImageApi(BASE, async (url) => {
    requestUrl = url;
    return valid();
  });
  const ref = await api.loadImageReference('img-123');
  assert.equal(requestUrl, `${BASE}api/v2/images/img-123`);
  assert.deepEqual(ref, {
    imageUid: 'img-123', imageUrl: `${BASE}files/stage/example.png`,
  });
});

test('empty image_url describes an unavailable file', () => {
  assert.deepEqual(parseImageReference(valid('abc', ''), 'abc', BASE), {
    imageUid: 'abc', imageUrl: null,
  });
});

test('UID cannot silently change between request and response', () => {
  assert.throws(() => parseImageReference(valid('other'), 'abc', BASE), ImageApiError);
});

test('non-objects and invalid URLs are rejected', () => {
  for (const invalid of [null, [], 5, { image_uid: 'abc' }]) {
    assert.throws(() => parseImageReference(invalid, 'abc', BASE), ImageApiError);
  }
  for (const url of [
    'https://third-party.example/tracker.png',
    '/api/v2/admin',
    '/files/../api/v2/admin',
    '//evil.test/files/asset.png',
  ]) {
    assert.throws(() => parseImageReference(valid('abc', url), 'abc', BASE), ImageApiError);
  }
});

test('UID is encoded and validation prevents path confusion', async () => {
  const api = new ComfyReviewImageApi(BASE, async (_url) => valid('a b', ''));
  await api.loadImageReference('a b');
  for (const bad of ['', ' bad', '../bad', '..', 'x/y', 'x?y', 'x#y', 'a\\b']) {
    await assert.rejects(api.loadImageReference(bad), ImageApiError);
  }
});

test('unsupported protocols and credentials are rejected', () => {
  assert.throws(() => new ComfyReviewImageApi('file:///tmp/a'), ImageApiError);
  assert.throws(() => new ComfyReviewImageApi('http://admin:pass@localhost:8000'), ImageApiError);
});

test('requester rejects HTTP failures before parsing body', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({ ok: false, status: 404 });
    await assert.rejects(requestJsonWithFetch(BASE), (error) => {
      assert.equal(error.kind, 'http');
      assert.equal(error.httpStatus, 404);
      return true;
    });
  } finally {
    globalThis.fetch = original;
  }
});

test('requester passes AbortSignal and omits ambient credentials', async () => {
  const original = globalThis.fetch;
  const controller = new AbortController();
  try {
    let observed;
    globalThis.fetch = async (url, options) => {
      observed = { url, options };
      return { ok: true, json: async () => valid() };
    };
    const result = await requestJsonWithFetch(BASE, controller.signal);
    assert.deepEqual(result, valid());
    assert.equal(observed.options.signal, controller.signal);
    assert.equal(observed.options.credentials, 'omit');
  } finally {
    globalThis.fetch = original;
  }
});
