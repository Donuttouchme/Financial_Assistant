import type { ApiError } from "./types";

export class HttpError extends Error implements ApiError {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`HTTP ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

async function parseError(response: Response): Promise<HttpError> {
  let detail = response.statusText || "Request failed";
  try {
    const body = await response.json();
    if (body && typeof body.detail === "string") detail = body.detail;
  } catch {
    /* body not JSON */
  }
  return new HttpError(response.status, detail);
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function apiFetchBlob(path: string): Promise<Blob> {
  const response = await fetch(path);
  if (!response.ok) throw await parseError(response);
  return response.blob();
}
