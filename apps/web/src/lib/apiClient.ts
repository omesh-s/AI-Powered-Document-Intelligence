import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "./authStorage";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`HTTP ${status}`);
    this.name = "ApiError";
  }
}

/** Human-readable message for API or presigned PUT failures. */
export function formatApiError(err: unknown): string {
  if (err instanceof ApiError) {
    const b = err.body;
    if (b && typeof b === "object" && "error" in b) {
      const inner = (b as { error?: { code?: string; message?: string } }).error;
      if (inner?.message) {
        return inner.code ? `${inner.code}: ${inner.message}` : inner.message;
      }
    }
    if (typeof b === "string" && b.trim()) {
      return b.length > 500 ? `${b.slice(0, 500)}…` : b;
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Request failed";
}

async function parseJson<T>(r: Response): Promise<T> {
  const t = await r.text();
  if (!t) return undefined as T;
  return JSON.parse(t) as T;
}

let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  const rt = getRefreshToken();
  if (!rt) return false;
  refreshPromise = (async () => {
    try {
      const r = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: rt }),
      });
      if (!r.ok) return false;
      const data = (await r.json()) as {
        tokens: { access_token: string; refresh_token: string };
      };
      setTokens(data.tokens.access_token, data.tokens.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

export type RequestOptions = RequestInit & {
  /** Set false for login/register */
  auth?: boolean;
};

export async function apiRequest<T>(path: string, init: RequestOptions = {}): Promise<T> {
  const { auth = true, headers: initHeaders, ...rest } = init;
  const headers = new Headers(initHeaders);
  if (!headers.has("Content-Type") && rest.body && typeof rest.body === "string") {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const at = getAccessToken();
    if (at) headers.set("Authorization", `Bearer ${at}`);
  }
  const url = path.startsWith("http") ? path : `/api${path.startsWith("/") ? path : `/${path}`}`;
  let r = await fetch(url, { ...rest, headers });
  if (r.status === 401 && auth) {
    const ok = await tryRefresh();
    if (ok) {
      const at2 = getAccessToken();
      if (at2) headers.set("Authorization", `Bearer ${at2}`);
      r = await fetch(url, { ...rest, headers });
    } else {
      clearTokens();
    }
  }
  if (!r.ok) {
    const body = await parseJson(r).catch(() => null);
    throw new ApiError(r.status, body);
  }
  return parseJson<T>(r);
}

export async function apiUploadPut(url: string, file: File, requiredHeaders: Record<string, string>) {
  const headers = new Headers(requiredHeaders);
  const r = await fetch(url, { method: "PUT", headers, body: file });
  if (!r.ok) {
    throw new ApiError(r.status, await r.text().catch(() => null));
  }
}
