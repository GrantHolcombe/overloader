// Cloudflare Worker "overloader-edge", route <app hostname>/* (overloader.hiregrant.today/* for now)
//
// The app's front door. One hostname for everything, so the PWA and its API share an origin
// (no CORS) and the Lambda behind it is only reachable through here:
//
//   /api/*   -> the API's Lambda Function URL, with the X-Origin-Verify secret (the API refuses
//               requests without it) and the visitor's IP as X-Client-IP (for the sign-in rate
//               limit; anything a browser sent under that name is overwritten).
//   anything else -> the built PWA in S3 (the bucket only answers Cloudflare's addresses). App
//               routes like /exercise/56 aren't files, so they get index.html and the Vue router
//               takes over.
//
// Settings (dashboard: Workers & Pages > overloader-edge > Settings > Variables and Secrets):
//   API_ORIGIN     plain text  the Function URL, e.g. https://abc.lambda-url.us-west-2.on.aws/
//   SITE_ORIGIN    plain text  the bucket's website endpoint (web stack output WebsiteOrigin)
//   ORIGIN_SECRET  secret      the same value as the api stack's OriginSecret parameter
//
// Deploy: paste this file into the Worker in the Cloudflare dashboard and click Deploy.

const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Strict-Transport-Security": "max-age=31536000",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.protocol === "http:") {
      url.protocol = "https:";
      return Response.redirect(url.toString(), 301);
    }
    if (url.pathname === "/api" || url.pathname.startsWith("/api/")) {
      return proxyApi(request, url, env);
    }
    return serveSite(request, url, env);
  },
};

async function proxyApi(request, url, env) {
  if (!env.API_ORIGIN || !env.ORIGIN_SECRET) {
    return json({ detail: "API not configured" }, 503);
  }
  const target = new URL(url.pathname + url.search, env.API_ORIGIN);
  const headers = new Headers(request.headers);
  headers.set("X-Origin-Verify", env.ORIGIN_SECRET);
  headers.set("X-Client-IP", request.headers.get("CF-Connecting-IP") || "");
  const hasBody = !["GET", "HEAD"].includes(request.method);
  try {
    return await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? request.body : undefined,
      redirect: "manual",
    });
  } catch {
    return json({ detail: "Can't reach the API right now. Try again in a moment." }, 502);
  }
}

async function serveSite(request, url, env) {
  if (!["GET", "HEAD"].includes(request.method)) {
    return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
  }
  const origin = env.SITE_ORIGIN.replace(/\/$/, "");
  let res = await fetch(origin + url.pathname, { method: request.method });
  // Not a file: an app route (no extension in the last path segment) gets the app shell.
  const lastSegment = url.pathname.split("/").pop() || "";
  if (res.status === 404 && !lastSegment.includes(".")) {
    res = await fetch(origin + "/index.html", { method: request.method });
  }
  const out = new Response(res.body, res);
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) out.headers.set(name, value);
  // Only the hashed build files under /assets/ may be cached. Everything else (index.html, the
  // service worker, the manifest, icons) must be revalidated, or app updates get stuck on
  // phones. Set here because the zone's Browser Cache TTL otherwise replaces S3's no-cache.
  if (!url.pathname.startsWith("/assets/")) out.headers.set("Cache-Control", "no-cache");
  return out;
}

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...SECURITY_HEADERS },
  });
}
