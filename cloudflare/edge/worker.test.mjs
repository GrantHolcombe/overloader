import assert from "node:assert/strict";
// Routing checks for the Worker with a fake fetch:  node cloudflare/edge/worker.test.mjs
const mod = await import("./worker.js");
const worker = mod.default;
const env = { API_ORIGIN: "https://fn.lambda-url.us-west-2.on.aws/", SITE_ORIGIN: "http://bucket.s3-website-us-west-2.amazonaws.com", ORIGIN_SECRET: "s3cret" };
const calls = [];
const files = { "/index.html": "<div id=\"app\"></div>", "/assets/app-1.js": "js" };
globalThis.fetch = async (url, init = {}) => {
  const u = new URL(url);
  calls.push({ url: u.toString(), init });
  if (u.host.startsWith("fn.")) return new Response('{"ok":true}', { status: 200, headers: { "content-type": "application/json" } });
  const body = files[u.pathname];
  return body ? new Response(body, { status: 200 }) : new Response("NoSuchKey", { status: 404 });
};
const req = (path, opts = {}) => new Request("https://overloader.hiregrant.today" + path, opts);

// API: proxied with the secret and the client IP; a forged X-Client-IP is overwritten.
let r = await worker.fetch(req("/api/health?x=1", { headers: { "CF-Connecting-IP": "203.0.113.9", "X-Client-IP": "6.6.6.6" } }), env);
assert.equal(r.status, 200);
let c = calls.at(-1);
assert.equal(c.url, "https://fn.lambda-url.us-west-2.on.aws/api/health?x=1");
assert.equal(c.init.headers.get("x-origin-verify"), "s3cret");
assert.equal(c.init.headers.get("x-client-ip"), "203.0.113.9");

// POST bodies pass through.
r = await worker.fetch(req("/api/auth/request-code", { method: "POST", body: '{"email":"a@b.c"}', headers: { "content-type": "application/json" } }), env);
assert.equal(calls.at(-1).init.method, "POST");
assert.ok(calls.at(-1).init.body);

// Site: files served, app routes get index.html with 200, missing assets stay 404.
r = await worker.fetch(req("/assets/app-1.js"), env);
assert.equal(r.status, 200); assert.equal(await r.text(), "js");
r = await worker.fetch(req("/exercise/56"), env);
assert.equal(r.status, 200); assert.match(await r.text(), /id="app"/);
assert.equal(r.headers.get("x-content-type-options"), "nosniff");
r = await worker.fetch(req("/assets/missing.js"), env);
assert.equal(r.status, 404);
r = await worker.fetch(req("/", {}), env);
assert.equal(r.status, 200);

// Only GET/HEAD for the site; http goes to https; missing config is a clear 503.
r = await worker.fetch(req("/", { method: "POST" }), env);
assert.equal(r.status, 405);
r = await worker.fetch(new Request("http://overloader.hiregrant.today/x"), env);
assert.equal(r.status, 301); assert.equal(r.headers.get("location"), "https://overloader.hiregrant.today/x");
r = await worker.fetch(req("/api/health"), { SITE_ORIGIN: env.SITE_ORIGIN });
assert.equal(r.status, 503);
console.log("worker routing: all checks pass");
