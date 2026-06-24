/**
 * Cloudflare Pages Function: per-article page view counter (KV).
 * Bind KV namespace as PAGE_VIEWS in Pages → Settings → Functions.
 */

const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
};

function normalizePath(raw) {
  if (!raw) return "";
  let path = String(raw).trim().replace(/^\/+/, "");
  try {
    path = decodeURIComponent(path);
  } catch (_) {
    /* keep raw */
  }
  return path;
}

function isValidPostPath(path) {
  return path.startsWith("posts/") && path.endsWith(".html") && !path.includes("..");
}

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const path = normalizePath(url.searchParams.get("path"));

  if (!isValidPostPath(path)) {
    return new Response(JSON.stringify({ error: "invalid_path" }), {
      status: 400,
      headers: JSON_HEADERS,
    });
  }

  const kv = env.PAGE_VIEWS;
  if (!kv) {
    return new Response(JSON.stringify({ error: "kv_unbound", views: null }), {
      status: 503,
      headers: JSON_HEADERS,
    });
  }

  if (request.method === "GET") {
    const views = parseInt((await kv.get(path)) || "0", 10);
    return new Response(JSON.stringify({ views }), { headers: JSON_HEADERS });
  }

  if (request.method === "POST") {
    const current = parseInt((await kv.get(path)) || "0", 10);
    const views = current + 1;
    await kv.put(path, String(views));
    return new Response(JSON.stringify({ views }), { headers: JSON_HEADERS });
  }

  return new Response(JSON.stringify({ error: "method_not_allowed" }), {
    status: 405,
    headers: JSON_HEADERS,
  });
}
