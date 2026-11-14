import { test, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { analyzeMedia, checkBackend, ApiError, apiUrl } from '../src/api.ts';

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'content-type': 'application/json' },
});
const health = () => json({ status: 'ok', service: 'VeriSight API', neural_detector: 'ready' });

test('hosted requests use the API origin and local requests retain the proxy path', () => {
  assert.equal(apiUrl('/api/v1/analyze', ' https://api.example.com/// '), 'https://api.example.com/api/v1/analyze');
  assert.equal(apiUrl('/api/v1/health', ''), '/api/v1/health');
});

test('network failure explains how to start the backend', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
  await assert.rejects(checkBackend(), error => error instanceof ApiError && error.status === 0 && /npm run dev/.test(error.message));
});

test('offline proxy errors give startup instructions', async () => {
  for (const status of [500, 502, 503, 504]) {
    globalThis.fetch = async () => new Response('', { status });
    await assert.rejects(checkBackend(), /Application startup complete/);
  }
});

test('a static server serving HTML identifies the wrong address', async () => {
  globalThis.fetch = async () => new Response('<html>App</html>', { headers: { 'content-type': 'text/html' } });
  await assert.rejects(checkBackend(), /localhost:5173/);
});

test('unreachable backend prevents the upload', async () => {
  const requests = [];
  globalThis.fetch = async url => { requests.push(url); throw new TypeError('Failed to fetch'); };
  await assert.rejects(analyzeMedia(new File(['image'], 'test.png')), /couldn’t reach/);
  assert.deepEqual(requests, ['/api/v1/health']);
});

test('retry sends the original file after connectivity returns', async () => {
  const file = new File(['original bytes'], 'test.png', { type: 'image/png' });
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
  await assert.rejects(analyzeMedia(file));
  const report = { detection: { status: 'complete', ai_score: 0.42 } };
  globalThis.fetch = async (url, options) => {
    if (url.endsWith('/health')) return health();
    assert.equal(options.method, 'POST');
    assert.equal(await options.body.get('file').text(), 'original bytes');
    return json(report);
  };
  assert.deepEqual(await analyzeMedia(file), report);
});

test('connection loss during upload is readable and file errors stay specific', async () => {
  globalThis.fetch = async url => {
    if (url.endsWith('/health')) return health();
    throw new TypeError('Failed to fetch');
  };
  await assert.rejects(analyzeMedia(new File(['x'], 'test.png')), /couldn’t reach/);
  globalThis.fetch = async url => url.endsWith('/health') ? health() : json({ detail: 'This image is damaged.' }, 400);
  await assert.rejects(analyzeMedia(new File(['x'], 'test.png')), /This image is damaged/);
});
