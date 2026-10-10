import createClient from "openapi-fetch";
import type { components, paths } from "./generated";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export const endpoint = (path: string) =>
  `/api/backend/v1/${path.replace(/^\//, "")}`;
export async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const response = await fetch(endpoint(path), {
    method: method ?? (body === undefined ? "GET" : "POST"),
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail ?? data.error ?? response.statusText);
    throw new ApiError(detail, response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export type RecordData = Record<string, unknown> & { id: string };
export type Entity = RecordData & {
  name: string;
  type: string;
  description: string;
  fields: Record<string, unknown>;
  version: number;
};
export function str(value: unknown): string {
  if (value === null || value === undefined) return "—";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
export function rows(value: unknown): RecordData[] {
  return Array.isArray(value) ? value : [];
}
export function object(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}
export function time(value: unknown): string {
  if (!value) return "—";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime())
    ? str(value)
    : date.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}
export type { components, paths } from "./generated";

// Typed requests share the same authenticated gateway as the dynamic admin views.
// Paths include /v1, so the proxy base intentionally ends at /api/backend.
export const apiClient = createClient<paths>({
  baseUrl: "/api/backend",
  credentials: "same-origin",
  cache: "no-store",
  fetch: (request) => fetch(request),
});
export type EntityCreate = components["schemas"]["EntityCreate"];
export type EntityUpdate = components["schemas"]["EntityUpdate"];
