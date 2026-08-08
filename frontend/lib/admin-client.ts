"use client";

async function staffFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  try {
    const res = await fetch(`/api/admin/${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = (await res.json()) as { detail?: string };
        if (typeof body.detail === "string") detail = body.detail;
      } catch {
        // keep
      }
      return { ok: false, error: detail || `HTTP ${res.status}` };
    }
    if (res.status === 204) return { ok: true, data: undefined as T };
    const text = await res.text();
    if (!text) return { ok: true, data: undefined as T };
    return { ok: true, data: JSON.parse(text) as T };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : "Request failed",
    };
  }
}

export { staffFetch };
