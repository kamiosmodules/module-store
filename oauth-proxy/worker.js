
/**
 * Cloudflare Worker proxy for GitHub OAuth Device Flow.
 *
 * Routes:
 *   POST /device/code
 *   POST /access_token
 *
 * Required Worker configuration:
 *   GITHUB_CLIENT_ID - OAuth App client ID (Worker secret)
 *   ALLOWED_ORIGINS  - comma-separated exact browser origins
 */

const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store, max-age=0",
  "Pragma": "no-cache",
  "X-Content-Type-Options": "nosniff",
};

const MAX_REQUEST_BYTES = 8 * 1024;
const MAX_DEVICE_CODE_LENGTH = 2048;

function getAllowedOrigins(env) {
  return String(env.ALLOWED_ORIGINS || "")
    .split(",")
    .map(value => value.trim())
    .filter(Boolean);
}

function corsHeaders(origin) {
  const headers = new Headers(JSON_HEADERS);
  headers.set("Vary", "Origin");
  headers.set("Access-Control-Allow-Origin", origin);
  headers.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type");
  headers.set("Access-Control-Max-Age", "86400");
  return headers;
}

function jsonResponse(data, status, origin) {
  const headers = origin
    ? corsHeaders(origin)
    : new Headers(JSON_HEADERS);

  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers,
  });
}

function errorResponse(error, status, origin, description) {
  const body = { error };
  if (description) body.error_description = description;
  return jsonResponse(body, status, origin);
}

async function readJson(request) {
  const contentType = request.headers.get("Content-Type") || "";

  if (!contentType.toLowerCase().includes("application/json")) {
    throw new Error("content_type_must_be_application_json");
  }

  const declaredLength = Number(
    request.headers.get("Content-Length") || 0
  );

  if (declaredLength > MAX_REQUEST_BYTES) {
    throw new Error("request_too_large");
  }

  const raw = await request.text();

  if (new TextEncoder().encode(raw).byteLength > MAX_REQUEST_BYTES) {
    throw new Error("request_too_large");
  }

  let value;

  try {
    value = raw ? JSON.parse(raw) : {};
  } catch {
    throw new Error("invalid_json");
  }

  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("json_body_must_be_an_object");
  }

  return value;
}

async function forwardToGitHub(endpoint, parameters) {
  const upstream = await fetch(endpoint, {
    method: "POST",
    redirect: "error",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams(parameters).toString(),
  });

  const raw = await upstream.text();
  let data;

  try {
    data = JSON.parse(raw);
  } catch {
    return {
      status: 502,
      data: {
        error: "invalid_upstream_response",
        error_description: "GitHub returned an unreadable OAuth response.",
      },
    };
  }

  return {
    status: upstream.status,
    data,
  };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowedOrigins = getAllowedOrigins(env);

    // Exact origin matching. Never use wildcard CORS.
    if (!origin || !allowedOrigins.includes(origin)) {
      return errorResponse("origin_not_allowed", 403, null);
    }

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": origin,
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
          "Access-Control-Max-Age": "86400",
          "Vary": "Origin",
        },
      });
    }

    if (request.method !== "POST") {
      return errorResponse("method_not_allowed", 405, origin);
    }

    const url = new URL(request.url);

    if (url.search || url.hash) {
      return errorResponse(
        "query_parameters_not_supported",
        400,
        origin
      );
    }

    if (!env.GITHUB_CLIENT_ID ||
        typeof env.GITHUB_CLIENT_ID !== "string") {
      return errorResponse("missing_github_client_id", 500, origin);
    }

    let input;

    try {
      input = await readJson(request);
    } catch (error) {
      return errorResponse(
        error.message || "invalid_request",
        400,
        origin
      );
    }

    const clientId = env.GITHUB_CLIENT_ID.trim();

    if (!clientId) {
      return errorResponse("missing_github_client_id", 500, origin);
    }

    let endpoint;
    const parameters = {
      client_id: clientId,
    };

    if (url.pathname === "/device/code") {
      // Scope is fixed. Callers cannot request wider permissions.
      parameters.scope = "public_repo";

      endpoint = "https://github.com/login/device/code";

    } else if (url.pathname === "/access_token") {
      const deviceCode = input.device_code;

      if (
        typeof deviceCode !== "string" ||
        deviceCode.trim().length === 0 ||
        deviceCode.length > MAX_DEVICE_CODE_LENGTH
      ) {
        return errorResponse("invalid_device_code", 400, origin);
      }

      parameters.device_code = deviceCode;

      parameters.grant_type =
        "urn:ietf:params:oauth:grant-type:device_code";

      endpoint = "https://github.com/login/oauth/access_token";

    } else {
      return errorResponse("not_found", 404, origin);
    }

    try {
      const result = await forwardToGitHub(endpoint, parameters);

      return jsonResponse(
        result.data,
        result.status,
        origin
      );

    } catch {
      return errorResponse(
        "github_unreachable",
        502,
        origin,
        "GitHub OAuth could not be reached. Please try again."
      );
    }
  },
};
