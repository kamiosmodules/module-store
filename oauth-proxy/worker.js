/**
 * Minimal Cloudflare Worker proxy for GitHub OAuth Device Flow.
 * It forwards only the two device-flow endpoints, stores no tokens, and
 * accepts requests only from origins listed in ALLOWED_ORIGINS.
 *
 * Worker variables:
 *   GITHUB_CLIENT_ID  - GitHub OAuth App client ID
 *   ALLOWED_ORIGINS   - comma-separated exact origins, for example:
 *                       https://kamiosmodules.github.io,http://localhost:8000
 */

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

function jsonResponse(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status: status || 200,
    headers: {
      ...JSON_HEADERS,
      "access-control-allow-origin": origin,
      "access-control-allow-methods": "POST, OPTIONS",
      "access-control-allow-headers": "Content-Type",
      "access-control-max-age": "86400",
      "vary": "Origin",
    },
  });
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowedOrigins = String(env.ALLOWED_ORIGINS || "")
      .split(",")
      .map(value => value.trim())
      .filter(Boolean);

    if (!origin || !allowedOrigins.includes(origin)) {
      return new Response("Origin not allowed", { status: 403 });
    }

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": origin,
          "access-control-allow-methods": "POST, OPTIONS",
          "access-control-allow-headers": "Content-Type",
          "access-control-max-age": "86400",
          "vary": "Origin",
        },
      });
    }

    if (request.method !== "POST") return jsonResponse({ error: "method_not_allowed" }, 405, origin);
    if (!env.GITHUB_CLIENT_ID) return jsonResponse({ error: "missing_github_client_id" }, 500, origin);

    const url = new URL(request.url);
    let input;
    try {
      input = await request.json();
    } catch {
      return jsonResponse({ error: "invalid_json" }, 400, origin);
    }

    let endpoint;
    const params = new URLSearchParams({ client_id: env.GITHUB_CLIENT_ID });

    if (url.pathname === "/device/code") {
      // The requested scope is intentionally fixed; callers cannot widen it.
      params.set("scope", "public_repo");
      endpoint = "https://github.com/login/device/code";
    } else if (url.pathname === "/access_token") {
      const deviceCode = String(input.device_code || "");
      if (!deviceCode || deviceCode.length > 256) {
        return jsonResponse({ error: "invalid_device_code" }, 400, origin);
      }
      params.set("device_code", deviceCode);
      params.set("grant_type", "urn:ietf:params:oauth:grant-type:device_code");
      endpoint = "https://github.com/login/oauth/access_token";
    } else {
      return jsonResponse({ error: "not_found" }, 404, origin);
    }

    try {
      const upstream = await fetch(endpoint, {
        method: "POST",
        headers: {
          "accept": "application/json",
          "content-type": "application/x-www-form-urlencoded",
        },
        body: params.toString(),
      });
      const body = await upstream.json();
      return jsonResponse(body, upstream.status, origin);
    } catch {
      return jsonResponse({ error: "github_unreachable", error_description: "GitHub OAuth could not be reached." }, 502, origin);
    }
  },
};
